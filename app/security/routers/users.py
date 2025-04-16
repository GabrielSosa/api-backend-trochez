from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.security.models.users import User
from app.security.models.user_types import UserType
from app.security.schemas.users import UserCreate, UserUpdate, UserInDB
from app.security.utils import get_password_hash, get_current_user

router = APIRouter()

@router.post("/", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo usuario.
    Solo usuarios autenticados pueden crear otros usuarios.
    """
    # Verificar si el tipo de usuario existe
    user_type = db.query(UserType).filter(UserType.id == user.user_type_id).first()
    if not user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de usuario especificado no existe"
        )
    
    # Verificar si el correo ya está registrado
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado"
        )
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        user_type_id=user.user_type_id,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserInDB])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener lista de usuarios.
    Solo usuarios autenticados pueden ver la lista.
    """
    return db.query(User).offset(skip).limit(limit).all()

@router.get("/me", response_model=UserInDB)
async def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Obtener información del usuario actual.
    """
    return current_user

@router.get("/{user_id}", response_model=UserInDB)
async def read_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener un usuario específico por ID.
    Solo usuarios autenticados pueden ver otros usuarios.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )
    return user

@router.put("/{user_id}", response_model=UserInDB)
async def update_user(
    user_id: int, 
    user: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar un usuario.
    Solo usuarios autenticados pueden actualizar usuarios.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )
    
    # Si se está actualizando el tipo de usuario, verificar que exista
    if user.user_type_id is not None:
        user_type = db.query(UserType).filter(UserType.id == user.user_type_id).first()
        if not user_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo de usuario especificado no existe"
            )
    
    update_data = user.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Eliminar un usuario.
    Solo usuarios autenticados pueden eliminar usuarios.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado"
        )
    db.delete(db_user)
    db.commit()
    return None 