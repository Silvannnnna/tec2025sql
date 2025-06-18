import sqlite3
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import re
from pypdf import PdfReader
import chromadb
import io
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from fastapi.staticfiles import StaticFiles

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Permitir CORS para frontend-backend (ajustar origen si es necesario)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto a tu dominio en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = "store.db"
templates = Jinja2Templates(directory="templates")

# Inicializar ChromaDB client (persistente en disco)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class QueryRequest(BaseModel):
    question: str

def adaptar_sql_para_sqlite(sql_query: str) -> str:
    # Reemplaza SELECT TOP N ... por SELECT ... LIMIT N
    import re
    # Detecta SELECT TOP N ... FROM ...
    top_match = re.match(r'(SELECT)\s+TOP\s+(\d+)\s+(.*?FROM\s+.+)', sql_query, re.IGNORECASE)
    if top_match:
        select, top_n, rest = top_match.groups()
        # Quita TOP N y agrega LIMIT N al final
        sql_query = f"{select} {rest} LIMIT {top_n}"
    # Reemplaza YEAR(Fecha) por strftime('%Y', Fecha)
    sql_query = re.sub(r'YEAR\(([^)]+)\)', r"strftime('%Y', \1)", sql_query, flags=re.IGNORECASE)
    # Reemplaza comillas simples dobles por simples
    sql_query = sql_query.replace("''", "'")
    return sql_query

@app.post("/ask")
def ask_question(req: QueryRequest):
    question = req.question
    # --- RAG: buscar contexto relevante en ChromaDB ---
    collection = chroma_client.get_or_create_collection("pdf_docs")
    # Obtener embedding de la pregunta
    embeddings = OpenAIEmbeddings()
    q_emb = embeddings.embed_query(question)
    # Buscar los fragmentos más relevantes
    results = collection.query(query_embeddings=[q_emb], n_results=3)
    context_chunks = results.get("documents", [[]])[0]
    context = "\n---\n".join(context_chunks) if context_chunks else ""
    # 1. Leer el prompt base desde archivo externo
    with open("prompt.txt", "r", encoding="utf-8") as f:
        prompt_base = f.read()
    # Inyectar contexto si existe
    if context:
        prompt = f"Contexto relevante extraído del PDF:\n{context}\n\nPregunta: {question}"
    else:
        prompt = prompt_base.replace("{question}", question)
    # 2. Consultar a OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content
    # 3. Extraer el query SQL de la respuesta
    sql_blocks = re.findall(r'```sql\s*([\s\S]+?)\s*```', result, re.IGNORECASE)
    sql_query = None
    if sql_blocks:
        for block in sql_blocks:
            if re.search(r'\bSELECT\b|\bUPDATE\b|\bDELETE\b|\bINSERT\b', block, re.IGNORECASE):
                sql_query = block.strip()
                break
        if not sql_query:
            sql_query = sql_blocks[0].strip()
    else:
        lines = result.splitlines()
        for line in lines:
            if re.match(r'\s*(SELECT|UPDATE|DELETE|INSERT) ', line, re.IGNORECASE):
                sql_query = line.strip()
                break
    if not sql_query:
        # Si no hay SQL, devolver la respuesta generada como texto plano para el chat
        return {"response": f"<div style='margin-bottom:18px;'><b>Respuesta:</b><br>{result}</div>"}
    # --- ADAPTAR SQL PARA SQLITE ---
    sql_query = adaptar_sql_para_sqlite(sql_query)
    # 4. Ejecutar el query en la base de datos local
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
    except Exception as e:
        return {"response": f"Error al ejecutar el query SQL: {e}"}
    # 5. Construir la tabla HTML
    table_html = '<table border="1"><tr>' + ''.join(f'<th>{col}</th>' for col in columns) + '</tr>'
    for row in rows:
        table_html += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
    table_html += '</table>'
    # 6. Extraer la interpretación
    interp_match = re.search(r'Interpretaci[oó]n:\s*(.*?)\n(Resultados:|Query:|$)', result, re.DOTALL)
    interpretacion = interp_match.group(1).strip() if interp_match else ""
    interpretacion = interpretacion.split('Query:')[0].strip()
    # 7. Responder con interpretación, tabla real y query
    respuesta = (
        f"<div style='margin-bottom:18px;'><b>Interpretación:</b><br>{interpretacion}</div>"
        f"<div style='margin-bottom:18px; text-align:center;'>{table_html}</div>"
        f"<div class='small' style='margin-top:18px; color:#555;'><b>Query SQL generado:</b><br><code style='font-size:0.95em'>{sql_query}</code></div>"
    )
    return {"response": respuesta}

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Solo se permiten archivos PDF."}
    contents = await file.read()
    reader = PdfReader(io.BytesIO(contents))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Guardar texto en un archivo temporal o en memoria para el siguiente paso (vectorización)
    with open("last_uploaded_pdf.txt", "w", encoding="utf-8") as f:
        f.write(text)
    return {"message": "PDF cargado y texto extraído.", "chars": len(text)}

# Vectorizar y almacenar texto del PDF en ChromaDB
@app.post("/process_pdf")
def process_pdf():
    # Leer el texto extraído del PDF
    try:
        with open("last_uploaded_pdf.txt", "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        return {"error": f"No se encontró texto de PDF: {e}"}
    # Dividir el texto en fragmentos
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = splitter.create_documents([text])
    # Embeddings
    embeddings = OpenAIEmbeddings()
    # Crear colección en ChromaDB
    collection = chroma_client.get_or_create_collection("pdf_docs")
    # Limpiar colección anterior
    all_ids = collection.get()["ids"]
    if all_ids:
        collection.delete(ids=all_ids)
    # Vectorizar y almacenar
    for i, doc in enumerate(docs):
        emb = embeddings.embed_query(doc.page_content)
        collection.add(
            documents=[doc.page_content],
            embeddings=[emb],
            ids=[f"chunk_{i}"]
        )
    return {"message": f"PDF vectorizado y almacenado. Fragmentos: {len(docs)}"}