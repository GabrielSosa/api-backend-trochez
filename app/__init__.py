# Remove 'metadata' from the import if it doesn't exist in database.py
from app.database import Base, engine

# Las tablas ya existen, no necesitamos crearlas
# Base.metadata.create_all(bind=engine)