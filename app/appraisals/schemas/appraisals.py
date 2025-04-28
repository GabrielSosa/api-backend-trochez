from datetime import date
from decimal import Decimal
from typing import List
from pydantic import BaseModel, Field

class AppraisalDeductionsBase(BaseModel):
    description: str
    amount: Decimal = Field(..., ge=0, decimal_places=2)

class AppraisalDeductionsCreate(AppraisalDeductionsBase):
    pass

class AppraisalDeductions(AppraisalDeductionsBase):
    appraisal_deductions_id: int
    vehicle_appraisal_id: int

    class Config:
        from_attributes = True

class VehicleAppraisalBase(BaseModel):
    appraisal_date: date
    vehicle_description: str = Field(..., max_length=100)
    brand: str = Field(..., max_length=50)
    model_year: int = Field(..., ge=1900, le=date.today().year + 1)
    color: str = Field(..., max_length=20)
    mileage: int = Field(..., ge=0)
    fuel_type: str = Field(..., max_length=20)
    # Remove decimal_places from engine_size
    engine_size: Decimal = Field(..., ge=0)
    plate_number: str = Field(..., max_length=20)
    applicant: str = Field(..., max_length=100)
    owner: str = Field(..., max_length=100)
    # Remove decimal_places constraint
    appraisal_value_usd: Decimal = Field(..., ge=0)
    # Remove decimal_places constraint
    appraisal_value_trochez: Decimal = Field(..., ge=0)
    vin: str = Field(..., max_length=20)
    engine_number: str = Field(..., max_length=20)
    notes: str | None = None
    validity_days: int = Field(..., ge=0)
    validity_kms: int = Field(..., ge=0)
    # Remove decimal_places constraint from new optional fields
    apprasail_value_lower_cost: Decimal | None = Field(default=None, ge=0)
    apprasail_value_bank: Decimal | None = Field(default=None, ge=0)
    apprasail_value_lower_bank: Decimal | None = Field(default=None, ge=0)

class VehicleAppraisalCreate(VehicleAppraisalBase):
    deductions: List[AppraisalDeductionsCreate]

# Add a new schema for updating appraisals
class VehicleAppraisalUpdate(VehicleAppraisalBase):
    deductions: List[AppraisalDeductionsCreate] # Include deductions for update

class VehicleAppraisal(VehicleAppraisalBase):
    vehicle_appraisal_id: int
    deductions: List[AppraisalDeductions]

    class Config:
        from_attributes = True