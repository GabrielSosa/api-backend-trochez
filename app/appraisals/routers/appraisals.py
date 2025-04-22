from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.security.utils import get_current_user
from app.security.models.users import User
from app.appraisals.models.appraisals import VehicleAppraisal, AppraisalDeductions
# Import the new update schema
from app.appraisals.schemas.appraisals import VehicleAppraisalCreate, VehicleAppraisalUpdate, VehicleAppraisal as VehicleAppraisalSchema

router = APIRouter()

# --- CREATE Endpoint ---
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

# --- READ ALL Endpoint ---
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
    # Use joinedload to efficiently load deductions along with appraisals
    appraisals = db.query(VehicleAppraisal).options(joinedload(VehicleAppraisal.deductions)).offset(skip).limit(limit).all()
    return appraisals

# --- READ ONE Endpoint ---
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
    # Use joinedload here as well
    appraisal = db.query(VehicleAppraisal).options(joinedload(VehicleAppraisal.deductions)).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id
    ).first()
    if not appraisal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado"
        )
    return appraisal

# --- UPDATE Endpoint (New) ---
@router.put("/{vehicle_appraisal_id}", response_model=VehicleAppraisalSchema)
async def update_vehicle_appraisal(
    vehicle_appraisal_id: int,
    appraisal_update: VehicleAppraisalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar un avalúo de vehículo existente por ID.
    Reemplaza todos los campos y las deducciones.
    Requiere autenticación JWT.
    """
    # Find the existing appraisal, load deductions eagerly
    db_appraisal = db.query(VehicleAppraisal).options(
        joinedload(VehicleAppraisal.deductions)
    ).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id
    ).first()

    if not db_appraisal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado"
        )

    # Update the main appraisal fields
    update_data = appraisal_update.model_dump(exclude_unset=True, exclude={'deductions'}) # Exclude deductions for now
    for key, value in update_data.items():
        setattr(db_appraisal, key, value)

    # Replace deductions: Delete existing ones first
    # Iterate over a copy of the list when removing items
    for existing_deduction in list(db_appraisal.deductions):
        db.delete(existing_deduction)
    
    # Add new deductions from the update payload
    for deduction_data in appraisal_update.deductions:
        new_deduction = AppraisalDeductions(
            vehicle_appraisal_id=db_appraisal.vehicle_appraisal_id,
            description=deduction_data.description,
            amount=deduction_data.amount
        )
        db.add(new_deduction)
        # Associate with the parent appraisal (SQLAlchemy handles the relationship)
        # db_appraisal.deductions.append(new_deduction) # Not strictly necessary if cascade is set up

    db.commit()
    db.refresh(db_appraisal) # Refresh to get updated state including new deductions
    return db_appraisal

# --- DELETE Endpoint (Placeholder - Add if needed) ---
# @router.delete("/{vehicle_appraisal_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_vehicle_appraisal(
#     vehicle_appraisal_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     # ... implementation for delete ...
#     pass