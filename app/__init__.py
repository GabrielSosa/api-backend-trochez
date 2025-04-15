from app.database import Base, engine, metadata

# Las tablas ya existen, no necesitamos crearlas
# Base.metadata.create_all(bind=engine) 