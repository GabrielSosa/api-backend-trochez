from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.security.utils import get_current_user
from app.security.models.users import User
from app.appraisals.models.appraisals import VehicleAppraisal, AppraisalDeductions
from app.appraisals.schemas.appraisals import VehicleAppraisalCreate, VehicleAppraisal as VehicleAppraisalSchema

router = APIRouter()

@router.post("/", response_model=VehicleAppraisalSchema)
async def create_vehicle_appraisal(
    appraisal: VehicleAppraisalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo avalúo de vehículo con sus deducciones.
    Requiere autenticación JWT.
    """
    # Crear primero el avalúo del vehículo
    db_appraisal = VehicleAppraisal(
        appraisal_date=appraisal.appraisal_date,
        vehicle_description=appraisal.vehicle_description,
        brand=appraisal.brand,
        model_year=appraisal.model_year,
        color=appraisal.color,
        mileage=appraisal.mileage,
        fuel_type=appraisal.fuel_type,
        engine_size=appraisal.engine_size,
        plate_number=appraisal.plate_number,
        applicant=appraisal.applicant,
        owner=appraisal.owner,
        appraisal_value_usd=appraisal.appraisal_value_usd,
        appraisal_value_local=appraisal.appraisal_value_local,
        vin=appraisal.vin,
        engine_number=appraisal.engine_number,
        notes=appraisal.notes,
        validity_days=appraisal.validity_days,
        validity_kms=appraisal.validity_kms
    )
    db.add(db_appraisal)
    db.flush()  # Para obtener el ID generado

    # Crear las deducciones
    for deduction in appraisal.deductions:
        db_deduction = AppraisalDeductions(
            vehicle_appraisal_id=db_appraisal.vehicle_appraisal_id,
            description=deduction.description,
            amount=deduction.amount
        )
        db.add(db_deduction)
    
    db.commit()
    db.refresh(db_appraisal)
    return db_appraisal

@router.get("/", response_model=List[VehicleAppraisalSchema])
async def read_vehicle_appraisals(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener lista de avalúos de vehículos.
    Requiere autenticación JWT.
    """
    appraisals = db.query(VehicleAppraisal).offset(skip).limit(limit).all()
    return appraisals

@router.get("/{vehicle_appraisal_id}", response_model=VehicleAppraisalSchema)
async def read_vehicle_appraisal(
    vehicle_appraisal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener un avalúo específico por ID.
    Requiere autenticación JWT.
    """
    appraisal = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id
    ).first()
    if not appraisal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado"
        )
    return appraisal 