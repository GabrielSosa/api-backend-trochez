from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.security.routers import user_types, users, auth

app = FastAPI()

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
app.include_router(user_types.router, prefix="/api/security/user-types", tags=["user_types"])
app.include_router(users.router, prefix="/api/security/users", tags=["users"])
app.include_router(auth.router, prefix="/api/security", tags=["auth"])

