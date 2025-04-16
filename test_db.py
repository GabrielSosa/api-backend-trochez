from app.database import engine
from sqlalchemy import text, inspect

def test_connection():
    try:
        # Intentar ejecutar una consulta simple
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("¡Conexión exitosa a la base de datos!")
            
            # Obtener lista de tablas
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print("\nTablas existentes:")
            for table in tables:
                print(f"- {table}")
            
            # Mostrar estructura de la tabla users
            print("\nEstructura de la tabla users:")
            columns = inspector.get_columns("users")
            for column in columns:
                print(f"- {column['name']}: {column['type']}")
            
            return True
    except Exception as e:
        print("Error al conectar a la base de datos:")
        print(e)
        return False

if __name__ == "__main__":
    test_connection() 