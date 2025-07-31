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
    from decimal import Decimal
    
    # Force clean all data before creating the SQLAlchemy model
    def force_clean_value(value, field_type='string'):
        """Ensure all values are properly cleaned"""
        if value is None:
            if field_type == 'decimal_required':
                return Decimal('0')
            elif field_type == 'int_required':
                return 0
            else:
                return None
        
        if isinstance(value, str) and value.strip() == "":
            if field_type == 'decimal_required':
                return Decimal('0')
            elif field_type == 'decimal_optional':
                return None
            elif field_type == 'int_required':
                return 0
            elif field_type == 'int_optional':
                return None
            else:
                return value
        
        return value
    
    # Create the main appraisal with forced clean values
    db_appraisal = VehicleAppraisal(
        plate_number=force_clean_value(appraisal.plate_number),
        vin=force_clean_value(appraisal.vin),
        applicant=force_clean_value(appraisal.applicant),
        owner=force_clean_value(appraisal.owner),
        color=force_clean_value(appraisal.color),
        engine_number=force_clean_value(appraisal.engine_number),
        vehicle_description=force_clean_value(appraisal.vehicle_description),
        model_year=force_clean_value(appraisal.model_year, 'int_required'),
        appraisal_date=appraisal.appraisal_date,
        brand=force_clean_value(appraisal.brand),
        mileage=force_clean_value(appraisal.mileage, 'int_required'),
        fuel_type=force_clean_value(appraisal.fuel_type),
        engine_size=force_clean_value(appraisal.engine_size, 'decimal_required'),
        appraisal_value_usd=force_clean_value(appraisal.appraisal_value_usd, 'decimal_required'),
        appraisal_value_trochez=force_clean_value(appraisal.appraisal_value_trochez, 'decimal_required'),
        apprasail_value_lower_cost=force_clean_value(appraisal.apprasail_value_lower_cost, 'decimal_required'),
        apprasail_value_bank=force_clean_value(appraisal.apprasail_value_bank, 'decimal_required'),
        apprasail_value_lower_bank=force_clean_value(appraisal.apprasail_value_lower_bank, 'decimal_required'),
        notes=force_clean_value(appraisal.notes),
        validity_days=force_clean_value(appraisal.validity_days, 'int_required'),
        validity_kms=force_clean_value(appraisal.validity_kms, 'int_required'),
        extras=force_clean_value(appraisal.extras),
        vin_card=force_clean_value(appraisal.vin_card),
        engine_number_card=force_clean_value(appraisal.engine_number_card),
        modified_km=force_clean_value(appraisal.modified_km, 'decimal_optional'),
        extra_value=force_clean_value(appraisal.extra_value, 'decimal_optional'),
        discounts=force_clean_value(appraisal.discounts, 'decimal_optional'),
        bank_value_in_dollars=force_clean_value(appraisal.bank_value_in_dollars, 'decimal_optional'),
        total_deductions=force_clean_value(appraisal.total_deductions, 'decimal_optional'),
        referencia_original=force_clean_value(appraisal.referencia_original, 'decimal_optional'),
        cert=force_clean_value(appraisal.cert, 'int_optional'),
        is_deleted=False  # Por defecto en False
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
    from sqlalchemy import or_, cast, String, text, desc, nulls_last
    
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
    
    # Construir la consulta base con filtro de is_deleted=False
    base_query = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.is_deleted == False
    ).options(
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
    
    # Obtener los resultados paginados ordenados por fecha (más recientes primero, sin fecha al final)
    results = search_query.order_by(
        nulls_last(desc(VehicleAppraisal.appraisal_date))
    ).offset(offset).limit(limit).all()
    
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener todos los avalúos de vehículos con paginación.
    Requiere autenticación JWT.
    """
    from sqlalchemy import desc, nulls_last
    
    # Get total count with is_deleted=False filter
    total_count = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.is_deleted == False
    ).count()
    
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
    
    # Calculate offset based on page
    offset = (page - 1) * limit
    
    # Get paginated results with is_deleted=False filter and ordered by date
    appraisals = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.is_deleted == False
    ).options(
        joinedload(VehicleAppraisal.deductions)
    ).order_by(
        nulls_last(desc(VehicleAppraisal.appraisal_date))
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
    appraisal = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id,
        VehicleAppraisal.is_deleted == False
    ).options(
        joinedload(VehicleAppraisal.deductions)
    ).first()
    
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
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id,
        VehicleAppraisal.is_deleted == False
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

# --- DELETE Endpoint (Soft Delete) ---
@router.delete("/{vehicle_appraisal_id}", status_code=status.HTTP_200_OK)
async def delete_vehicle_appraisal(
    vehicle_appraisal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Eliminar un avalúo de vehículo (soft delete).
    Marca el registro como eliminado (is_deleted=True) sin borrarlo físicamente.
    Requiere autenticación JWT.
    """
    db_appraisal = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id,
        VehicleAppraisal.is_deleted == False
    ).first()
    
    if db_appraisal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado o ya eliminado"
        )
    
    # Soft delete: marcar como eliminado
    db_appraisal.is_deleted = True
    
    db.commit()
    
    return {
        "message": "Avalúo eliminado exitosamente",
        "vehicle_appraisal_id": vehicle_appraisal_id
    }

# --- DUPLICATE Endpoint ---
@router.post("/{vehicle_appraisal_id}/duplicate", response_model=VehicleAppraisalSchema)
async def duplicate_vehicle_appraisal(
    vehicle_appraisal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Duplicar un avalúo de vehículo y sus deducciones.
    Crea una copia exacta del avalúo original con is_deleted=False y fecha actual.
    Requiere autenticación JWT.
    """
    from datetime import date
    
    # Buscar el avalúo original
    original_appraisal = db.query(VehicleAppraisal).filter(
        VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id,
        VehicleAppraisal.is_deleted == False
    ).first()
    
    if original_appraisal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avalúo no encontrado o ya eliminado"
        )
    
    # Crear una copia del avalúo con fecha actual
    duplicated_appraisal = VehicleAppraisal(
        appraisal_date=date.today(),  # Fecha actual
        vehicle_description=original_appraisal.vehicle_description,
        brand=original_appraisal.brand,
        model_year=original_appraisal.model_year,
        color=original_appraisal.color,
        mileage=original_appraisal.mileage,
        fuel_type=original_appraisal.fuel_type,
        engine_size=original_appraisal.engine_size,
        plate_number=original_appraisal.plate_number,
        applicant=original_appraisal.applicant,
        owner=original_appraisal.owner,
        appraisal_value_usd=original_appraisal.appraisal_value_usd,
        appraisal_value_trochez=original_appraisal.appraisal_value_trochez,
        apprasail_value_lower_cost=original_appraisal.apprasail_value_lower_cost,
        apprasail_value_bank=original_appraisal.apprasail_value_bank,
        apprasail_value_lower_bank=original_appraisal.apprasail_value_lower_bank,
        vin=original_appraisal.vin,
        engine_number=original_appraisal.engine_number,
        notes=original_appraisal.notes,
        validity_days=original_appraisal.validity_days,
        validity_kms=original_appraisal.validity_kms,
        extras=original_appraisal.extras,
        vin_card=original_appraisal.vin_card,
        engine_number_card=original_appraisal.engine_number_card,
        modified_km=original_appraisal.modified_km,
        extra_value=original_appraisal.extra_value,
        discounts=original_appraisal.discounts,
        bank_value_in_dollars=original_appraisal.bank_value_in_dollars,
        referencia_original=original_appraisal.referencia_original,
        cert=original_appraisal.cert,
        is_deleted=False  # Asegurar que la copia no esté eliminada
    )
    
    db.add(duplicated_appraisal)
    db.flush()  # Obtener el ID del nuevo avalúo sin hacer commit
    
    # Duplicar las deducciones
    for original_deduction in original_appraisal.deductions:
        duplicated_deduction = AppraisalDeductions(
            vehicle_appraisal_id=duplicated_appraisal.vehicle_appraisal_id,
            description=original_deduction.description,
            amount=original_deduction.amount
        )
        db.add(duplicated_deduction)
    
    db.commit()
    db.refresh(duplicated_appraisal)
    
    # Devolver solo el avalúo duplicado para que coincida con el schema
    return duplicated_appraisal