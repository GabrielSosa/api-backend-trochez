from datetime import date
from decimal import Decimal, InvalidOperation
from typing import List
from pydantic import BaseModel, Field, field_validator

class AppraisalDeductionsBase(BaseModel):
    description: str
    amount: Decimal | None = Field(None, ge=0)

    @field_validator('amount', mode='before')
    @classmethod
    def validate_amount(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                v = Decimal(v)
            except (InvalidOperation, ValueError):
                return None
        if isinstance(v, Decimal):
            # Check if it's NaN or infinite
            if v.is_nan() or v.is_infinite():
                return None
        return v

class AppraisalDeductionsCreate(AppraisalDeductionsBase):
    pass

class AppraisalDeductions(AppraisalDeductionsBase):
    appraisal_deductions_id: int
    vehicle_appraisal_id: int

    class Config:
        from_attributes = True

class VehicleAppraisalBase(BaseModel):
    appraisal_date: date | None = None
    vehicle_description: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=50)
    model_year: int | None = Field(None, ge=1900, le=date.today().year + 1)
    color: str | None = Field(None, max_length=20)
    mileage: int | None = Field(None, ge=0)
    fuel_type: str | None = Field(None, max_length=20)
    engine_size: Decimal | None = Field(None, ge=0)
    plate_number: str | None = Field(None, max_length=20)
    applicant: str | None = Field(None, max_length=100)
    owner: str | None = Field(None, max_length=100)
    appraisal_value_usd: Decimal | None = Field(None, ge=0)
    appraisal_value_trochez: Decimal | None = Field(None, ge=0)
    vin: str | None = Field(None, max_length=20)
    engine_number: str | None = Field(None, max_length=20)
    notes: str | None = None
    validity_days: int | None = Field(None, ge=0)
    validity_kms: int | None = Field(None, ge=0)
    apprasail_value_lower_cost: Decimal | None = Field(default=None, ge=0)
    apprasail_value_bank: Decimal | None = Field(default=None, ge=0)
    apprasail_value_lower_bank: Decimal | None = Field(default=None, ge=0)
    extras: str | None = None
    vin_card: str | None = Field(default=None, max_length=20)
    engine_number_card: str | None = Field(default=None, max_length=20)
    modified_km: int | None = Field(default=None, ge=0)
    extra_value: Decimal | None = Field(default=None, ge=0)
    discounts: Decimal | None = Field(default=None, ge=0)
    bank_value_in_dollars: Decimal | None = Field(default=None, ge=0)
    referencia_original: str | None = Field(default=None, max_length=100)

    @field_validator('engine_size', 'appraisal_value_usd', 'appraisal_value_trochez', 
                    'apprasail_value_lower_cost', 'apprasail_value_bank', 'apprasail_value_lower_bank',
                    'extra_value', 'discounts', 'bank_value_in_dollars', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                v = Decimal(v)
            except (InvalidOperation, ValueError):
                return None
        if isinstance(v, Decimal):
            # Check if it's NaN or infinite
            if v.is_nan() or v.is_infinite():
                return None
        return v

    @field_validator('referencia_original', mode='before')
    @classmethod
    def validate_referencia_original(cls, v):
        if v is None:
            return None
        # Convert numeric values to string
        if isinstance(v, (int, float, Decimal)):
            return str(int(v)) if isinstance(v, (int, float)) else str(v)
        return v

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