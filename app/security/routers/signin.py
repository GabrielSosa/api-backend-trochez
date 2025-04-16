from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.security.models.users import User
from app.security.schemas.signin import SignInRequest, Token
from app.security.utils import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/security/signin")

@router.post("/signin/custom", response_model=Token)
async def signin_custom(
    signin_data: SignInRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint para iniciar sesión usando el formato personalizado.
    Si las credenciales son correctas, devuelve un token JWT.
    """
    return await authenticate_user(db, signin_data.email, signin_data.password)

@router.post("/signin", response_model=Token)
async def signin(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint para iniciar sesión usando OAuth2.
    Si las credenciales son correctas, devuelve un token JWT.
    """
    return await authenticate_user(db, form_data.username, form_data.password)

async def authenticate_user(db: Session, email: str, password: str) -> Token:
    """
    Función auxiliar para autenticar usuarios.
    """
    # Buscar usuario por email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña
    if not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar si el usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token de acceso
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.user_id,
            "user_type_id": user.user_type_id
        },
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        message="OK"
    ) 