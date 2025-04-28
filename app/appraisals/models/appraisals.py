from sqlalchemy import Column, Integer, String, Date, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from typing import ClassVar, Dict, Any

class VehicleAppraisal(Base):
    __tablename__ = "vehicle_appraisal"
    
    model_config = {
        "protected_namespaces": ()
    }

    vehicle_appraisal_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appraisal_date = Column(Date)
    vehicle_description = Column(String(100))
    brand = Column(String(50))
    model_year = Column(Integer)
    color = Column(String(20))
    mileage = Column(Integer)
    fuel_type = Column(String(20))
    engine_size = Column(Numeric(3, 1))
    plate_number = Column(String(20))
    applicant = Column(String(100))
    owner = Column(String(100))
    appraisal_value_usd = Column(Numeric(18, 2))
    appraisal_value_trochez = Column(Numeric(18, 2))
    apprasail_value_lower_cost = Column(Numeric(18, 2))
    apprasail_value_bank = Column(Numeric(18, 2))
    apprasail_value_lower_bank = Column(Numeric(18, 2))
    vin = Column(String(20))
    engine_number = Column(String(20))
    notes = Column(Text)
    validity_days = Column(Integer)
    validity_kms = Column(Integer)

    # Relación con AppraisalDeductions
    deductions = relationship("AppraisalDeductions", back_populates="vehicle_appraisal", cascade="all, delete-orphan")

class AppraisalDeductions(Base):
    __tablename__ = "appraisal_deductions"

    appraisal_deductions_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_appraisal_id = Column(Integer, ForeignKey("vehicle_appraisal.vehicle_appraisal_id", ondelete="CASCADE"), nullable=False)
    description = Column(Text)
    amount = Column(Numeric(10, 2))

    # Relación con VehicleAppraisal
    vehicle_appraisal = relationship("VehicleAppraisal", back_populates="deductions")
