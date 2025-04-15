# API de Gibson con FastAPI

Este es un proyecto de API REST desarrollado con FastAPI y MySQL.

## Requisitos

- Python 3.8+
- MySQL Server

## Instalación

1. Clonar el repositorio
2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar las variables de entorno:
   - Copiar el archivo `.env.example` a `.env`
   - Modificar las variables según tu configuración de MySQL

## Ejecución

Para iniciar el servidor de desarrollo:
```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Documentación

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 