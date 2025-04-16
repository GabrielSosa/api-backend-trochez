from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.core.config import settings

# Importar los routers
from app.security.routers import user_types_router, users_router, signin_router
from app.appraisals import appraisals_router

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

# Incluir los routers
app.include_router(user_types_router, prefix=f"{settings.API_V1_STR}/security/user-types", tags=["user-types"])
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/security/users", tags=["users"])
app.include_router(signin_router, prefix=f"{settings.API_V1_STR}/security", tags=["authentication"])
app.include_router(appraisals_router, prefix=f"{settings.API_V1_STR}/appraisals", tags=["appraisals"])

# Inicializar la base de datos
init_db()

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Gibson"}

