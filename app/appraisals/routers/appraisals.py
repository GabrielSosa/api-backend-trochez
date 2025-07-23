from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
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
    Crear un nuevo avalúo de vehículo.
    Requiere autenticación JWT.
    """
    # Create the main appraisal
    db_appraisal = VehicleAppraisal(
        plate_number=appraisal.plate_number,
        vin=appraisal.vin,
        applicant=appraisal.applicant,
        owner=appraisal.owner,
        color=appraisal.color,
        engine_number=appraisal.engine_number,
        vehicle_description=appraisal.vehicle_description,
        model_year=appraisal.model_year,
        appraisal_date=appraisal.appraisal_date,
        appraisal_value=appraisal.appraisal_value,
        modified_km=appraisal.modified_km,
        extra_value=appraisal.extra_value,
        discounts=appraisal.discounts,
        bank_value_in_dollars=appraisal.bank_value_in_dollars,
        referencia_original=appraisal.referencia_original,
        cert=appraisal.cert
    )
    db.add(db_appraisal)
    db.flush()  # Get the ID without committing

    # Create deductions
    for deduction_data in appraisal.deductions:
        deduction = AppraisalDeductions(
            vehicle_appraisal_id=db_appraisal.vehicle_appraisal_id,
            description=deduction_data.description,
            amount=deduction_data.amount
        )
        db.add(deduction)

    db.commit()
    db.refresh(db_appraisal)
    return db_appraisal

# --- SEARCH Endpoint ---
@router.get("/search")
async def search_vehicle_appraisals(
    query: str = Query("", description="Término de búsqueda"),
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Elementos por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Buscar avalúos por múltiples criterios.
    Busca en: placa, VIN, cliente, propietario, color, certificado, motor, modelo, año.
    Requiere autenticación JWT.
    """
    from sqlalchemy import or_, cast, String, text
    
    # Si no hay término de búsqueda, devolver todos los registros
    if not query or query.strip() == "":
        return {
            "data": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            },
            "message": "Debe proporcionar un término de búsqueda",
            "search_query": ""
        }
    
    # Construir la consulta base
    base_query = db.query(VehicleAppraisal).options(
        joinedload(VehicleAppraisal.deductions)
    )
    
    # Aplicar filtros de búsqueda con conversiones seguras
    search_query = base_query.filter(
        or_(
            VehicleAppraisal.plate_number.ilike(f"%{query}%"),
            VehicleAppraisal.vin.ilike(f"%{query}%"),
            VehicleAppraisal.applicant.ilike(f"%{query}%"),
            VehicleAppraisal.owner.ilike(f"%{query}%"),
            VehicleAppraisal.color.ilike(f"%{query}%"),
            # Convertir cert a string de forma segura
            cast(VehicleAppraisal.cert, String).ilike(f"%{query}%"),
            VehicleAppraisal.engine_number.ilike(f"%{query}%"),
            VehicleAppraisal.vehicle_description.ilike(f"%{query}%"),
            # Convertir model_year a string de forma segura
            cast(VehicleAppraisal.model_year, String).ilike(f"%{query}%")
        )
    )
    
    # Obtener el total de registros que coinciden con la búsqueda
    total_count = search_query.count()
    
    # Si no hay resultados, devolver respuesta vacía
    if total_count == 0:
        return {
            "data": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            },
            "message": f"No se encontraron avalúos para: '{query}'"
        }
    
    # Calcular paginación
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit
    
    # Validar si la página solicitada existe
    if page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Página {page} no existe. Solo hay {total_pages} páginas disponibles para la búsqueda."
        )
    
    # Obtener los resultados paginados
    results = search_query.offset(offset).limit(limit).all()
    
    # Determinar mensaje según el estado
    has_next = page < total_pages
    has_prev = page > 1
    
    if page == total_pages:
        message = f"Última página de resultados para: '{query}'"
    elif page == 1:
        message = f"Primera página de resultados para: '{query}'"
    else:
        message = f"Página {page} de {total_pages} para: '{query}'"
    
    return {
        "data": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "message": message,
        "search_query": query
    }

# --- READ ALL Endpoint ---
@router.get("/")
async def read_vehicle_appraisals(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Elementos por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento desde el inicio"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener todos los avalúos de vehículos con paginación.
    Requiere autenticación JWT.
    """
    # Get total count
    total_count = db.query(VehicleAppraisal).count()
    
    # If no data exists, return empty response
    if total_count == 0:
        return {
            "data": [],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            },
            "message": "No hay avalúos registrados en el sistema."
        }
    
    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit
    
    # Validate if requested page exists
    if page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Página {page} no existe. Solo hay {total_pages} páginas disponibles."
        )
    
    # Get paginated results
    appraisals = db.query(VehicleAppraisal).options(
        joinedload(VehicleAppraisal.deductions)
    ).offset(offset).limit(limit).all()
    
    # Determine message based on state
    has_next = page < total_pages
    has_prev = page > 1
    
    if page == total_pages:
        message = "Última página de avalúos"
    elif page == 1:
        message = "Primera página de avalúos"
    else:
        message = f"Página {page} de {total_pages}"
    
    return {
        "data": appraisals,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "message": message
    }

# --- READ ONE Endpoint ---
@router.get("/{vehicle_appraisal_id}", response_model=VehicleAppraisalSchema)
async def read_vehicle_appraisal(
    vehicle_appraisal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener un avalúo de vehículo específico por ID.
    Requiere autenticación JWT.
    """
    appraisal = db.query(VehicleAppraisal).options(
        joinedload(VehicleAppraisal.deductions)
    ).filter(VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id).first()
    
    if appraisal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado"
        )
    
    return appraisal

# --- UPDATE Endpoint ---
@router.put("/{vehicle_appraisal_id}", response_model=VehicleAppraisalSchema)
async def update_vehicle_appraisal(
    vehicle_appraisal_id: int,
    appraisal_update: VehicleAppraisalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar un avalúo de vehículo existente.
    Requiere autenticación JWT.
    """
    db_appraisal = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id
    ).first()
    
    if db_appraisal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado"
        )
    
    # This part implicitly handles the renamed and new fields
    # as long as VehicleAppraisalUpdate schema is correct.
    update_data = appraisal_update.model_dump(exclude_unset=True, exclude={'deductions'})
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