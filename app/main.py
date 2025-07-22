from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.core.config import settings

# Import the certificate router
from app.certs.certificate_routes import router as certificate_router

# Importar los routers
from app.security.routers import user_types_router, users_router, signin_router
from app.dashboard.routers.dashboard import router as dashboard_router
from app.appraisals import appraisals_router
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Incluir los routers
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/security/users", tags=["users"])
app.include_router(signin_router, prefix=f"{settings.API_V1_STR}/security", tags=["authentication"])
app.include_router(appraisals_router, prefix=f"{settings.API_V1_STR}/appraisals", tags=["appraisals"])
app.include_router(dashboard_router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
# Include the certificate routes
app.include_router(certificate_router)

# Inicializar la base de datos
init_db()

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Trochez"}

