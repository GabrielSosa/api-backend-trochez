from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# Create metadata object
metadata = MetaData()

# For Render PostgreSQL, we need to use a more specific connection string
# with explicit SSL parameters
DB_URL = os.environ.get("DATABASE_URL", None)

if not DB_URL:
    # Construct the database URL for PostgreSQL with explicit SSL parameters
    DB_URL = f"postgresql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

# Create the engine with modified configuration
engine = create_engine(
    DB_URL,
    # Remove SSL parameters from here as they're in the URL
    echo=False,  # Set to False in production
    pool_pre_ping=True,
    pool_recycle=300,
    # Add connect_args only if needed for local development
    # connect_args={"sslmode": "prefer"}
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

# Initialize database function
def init_db():
    """
    Initialize the database by creating all tables.
    This function should be called when the application starts.
    """
    # Import all models here to ensure they are registered with the Base metadata
    from app.security.models.users import User
    from app.security.models.user_types import UserType
    # Uncomment if these models exist
    # from app.appraisals.models.appraisals import VehicleAppraisal, AppraisalDeductions
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    return Base.metadata.create_all