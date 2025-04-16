from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.security.routers import user_types_router, users_router, signin_router

app = FastAPI(
    title="Trochez API",
    description="API para el sistema de avalúos Trochez",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar la base de datos
@app.on_event("startup")
async def startup_event():
    init_db()

# Incluir routers
app.include_router(user_types_router, prefix="/api/security/user-types", tags=["user-types"])
app.include_router(users_router, prefix="/api/security/users", tags=["users"])
app.include_router(signin_router, prefix="/api/security", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Trochez"}

