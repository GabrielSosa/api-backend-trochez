from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

# Importar la sesión de base de datos
from app.database import SessionLocal

# Corregir las importaciones para usar los modelos correctos
from app.appraisals.models.appraisals import VehicleAppraisal, AppraisalDeductions
from app.certs.certificate_service import CertificateService

router = APIRouter(
    prefix="/certificates",
    tags=["certificates"],
    responses={404: {"description": "Not found"}},
)

# Definir la dependencia para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/appraisal/{vehicle_appraisal_id}")
async def generate_appraisal_certificate(
    vehicle_appraisal_id: int,
    db: Session = Depends(get_db),
    download: Optional[bool] = False
):
    """
    Generate a PDF certificate for a vehicle appraisal.
    
    Args:
        vehicle_appraisal_id: ID of the vehicle appraisal
        db: Database session
        download: If True, the PDF will be downloaded, otherwise it will be displayed in the browser
    
    Returns:
        PDF file response
    """
    # Get the vehicle appraisal data
    appraisal = db.query(VehicleAppraisal).filter(VehicleAppraisal.vehicle_appraisal_id == vehicle_appraisal_id).first()
    if not appraisal:
        raise HTTPException(status_code=404, detail="Vehicle appraisal not found")
    
    # Get the deductions for this appraisal
    deductions = db.query(AppraisalDeductions).filter(
        AppraisalDeductions.vehicle_appraisal_id == vehicle_appraisal_id
    ).all()
    
    # Generate the PDF
    certificate_service = CertificateService()
    pdf_path = certificate_service.generate_certificate_pdf(appraisal, deductions)
    
    # Set the content disposition header based on download parameter
    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename=certificado_avaluo_{vehicle_appraisal_id}.pdf"
    else:
        headers["Content-Disposition"] = f"inline; filename=certificado_avaluo_{vehicle_appraisal_id}.pdf"
    
    # Return the PDF file
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers=headers,
        filename=f"certificado_avaluo_{vehicle_appraisal_id}.pdf"
    )