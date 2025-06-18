# Asistente Tienda IA - Tec de Monterrey

Asistente ejecutivo de análisis de datos de negocio para tiendas, especializado en consultas sobre ventas, productos y distribuidores usando una base de datos SQLite y FastAPI. Utiliza OpenAI GPT-4 para interpretar preguntas en español y generar consultas SQL automáticamente.

## Características

- Interfaz web amigable para hacer preguntas en lenguaje natural.
- Respuestas claras con interpretación, tabla de resultados y query SQL generado.
- Base de datos de ejemplo con productos, distribuidores y ventas.
- Backend en Python con FastAPI y conexión a OpenAI GPT-4.
- Adaptación automática de queries SQL a sintaxis SQLite.
- Respuestas en formato HTML con tablas y explicación.
- Modo oscuro dinámico y descarga de resultados en CSV.

## Estructura del Proyecto

```
.
├── .devcontainer/
│   └── devcontainer.json
├── templates/
│   └── index.html
├── create_db.py
├── main.py
├── prompt.txt
├── requirements.txt
├── store.db
├── .env
└── README.md
```

- `main.py`: Backend FastAPI, lógica de preguntas y respuestas.
- `create_db.py`: Script para crear y poblar la base de datos de ejemplo.
- `store.db`: Base de datos SQLite generada.
- `prompt.txt`: Prompt base para el modelo de lenguaje.
- `templates/index.html`: Interfaz web del chat.
- `.env`: Llave de API de OpenAI (no compartir públicamente).
- `requirements.txt`: Dependencias Python.
- `.devcontainer/`: Configuración para desarrollo en contenedores.

## Instalación y Ejecución

### 1. Requisitos

- Docker (opcional, recomendado para devcontainer)
- Python 3.11+
- Node.js y npm (solo si deseas modificar el frontend)
- Cuenta y API Key de OpenAI

### 2. Clonar el repositorio

```sh
git clone <url-del-repo>
cd tec2025sql
```

### 3. Crear y poblar la base de datos

```sh
python3 create_db.py
```

### 4. Instalar dependencias

```sh
pip install -r requirements.txt
```

### 5. Configurar la API Key de OpenAI

Crea un archivo `.env` con el contenido:

```
OPENAI_API_KEY=sk-...
```

### 6. Ejecutar el servidor

```sh
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Acceder a la aplicación

Abre en tu navegador: [http://localhost:8000](http://localhost:8000)

## Uso

1. Escribe una pregunta de negocio en español, por ejemplo:  
   _"¿Cuáles son los productos más vendidos este mes?"_
2. El asistente interpreta la pregunta, genera el query SQL, ejecuta la consulta y muestra:
   - Interpretación en texto.
   - Tabla de resultados (máx. 10 filas).
   - Query SQL generado.
   - Botón para descargar la tabla como CSV.

## Estructura de la Base de Datos

- **Productos**: Información de productos (clave, nombre, categoría, precios, etc).
- **Distribuidores**: Información de distribuidores (clave, municipio, estado, clasificación).
- **Ventas**: Registro de ventas (producto, distribuidor, unidades, fecha, descuento, etc).

Consulta la estructura detallada en `prompt.txt`.

## Personalización

- Modifica `prompt.txt` para ajustar el comportamiento del asistente.
- Cambia o expande los datos en `create_db.py` según tus necesidades.
- Edita el frontend en `templates/index.html` para personalizar la interfaz.

## Dependencias

- fastapi
- uvicorn
- openai==0.28
- pydantic
- jinja2
- langgraph
- langchain

Instalables con:

```sh
pip install -r requirements.txt
```

## Notas de Seguridad

- **No compartas tu archivo `.env` ni tu API Key de OpenAI.**
- El proyecto es solo para fines educativos y de demostración.

## Licencia

MIT

---

Desarrollado para el Tec de Monterrey.


