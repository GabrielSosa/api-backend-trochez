from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import pymysql

# Create metadata object
metadata = MetaData()

# Construct the database URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

# Create the engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600,  # Recycle connections older than 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base(metadata=metadata)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Add the missing init_db function
def init_db():
    """
    Initialize the database by creating all tables.
    This function should be called when the application starts.
    """
    # Import all models here to ensure they are registered with the Base metadata
    # For example:
    # from app.security.models.users import User
    # from app.appraisals.models.appraisals import VehicleAppraisal, AppraisalDeductions
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    return Base.metadata.create_all