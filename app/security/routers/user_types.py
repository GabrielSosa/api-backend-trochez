from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.security.models.user_types import UserType
from app.security.schemas.user_types import UserTypeCreate, UserTypeUpdate, UserTypeInDB

router = APIRouter(
    prefix="/api/security/user-types",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=UserTypeInDB, status_code=status.HTTP_201_CREATED)
def create_user_type(user_type: UserTypeCreate, db: Session = Depends(get_db)):
    # Verificar si ya existe un tipo de usuario con el mismo código
    db_user_type = db.query(UserType).filter(UserType.code == user_type.code).first()
    if db_user_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un tipo de usuario con este código"
        )
    
    db_user_type = UserType(**user_type.model_dump())
    db.add(db_user_type)
    db.commit()
    db.refresh(db_user_type)
    return db_user_type

@router.get("/", response_model=List[UserTypeInDB])
def read_user_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    user_types = db.query(UserType).offset(skip).limit(limit).all()
    return user_types

@router.get("/{user_type_id}", response_model=UserTypeInDB)
def read_user_type(user_type_id: int, db: Session = Depends(get_db)):
    db_user_type = db.query(UserType).filter(UserType.user_type_id == user_type_id).first()
    if db_user_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de usuario no encontrado"
        )
    return db_user_type

@router.put("/{user_type_id}", response_model=UserTypeInDB)
def update_user_type(user_type_id: int, user_type: UserTypeUpdate, db: Session = Depends(get_db)):
    db_user_type = db.query(UserType).filter(UserType.user_type_id == user_type_id).first()
    if db_user_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de usuario no encontrado"
        )
    
    # Verificar si el nuevo código ya existe en otro registro
    if user_type.code and user_type.code != db_user_type.code:
        existing_user_type = db.query(UserType).filter(
            UserType.code == user_type.code,
            UserType.user_type_id != user_type_id
        ).first()
        if existing_user_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un tipo de usuario con este código"
            )
    
    # Actualizar solo los campos proporcionados
    update_data = user_type.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user_type, key, value)
    
    db.commit()
    db.refresh(db_user_type)
    return db_user_type

@router.delete("/{user_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_type(user_type_id: int, db: Session = Depends(get_db)):
    db_user_type = db.query(UserType).filter(UserType.user_type_id == user_type_id).first()
    if db_user_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de usuario no encontrado"
        )
    
    db.delete(db_user_type)
    db.commit()
    return None 