import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

def migrate():
    with engine.begin() as conn:
        print("Agregando métricas a photo_requests...")
        
        # Add agent_response_time_minutes
        try:
            conn.execute(text("ALTER TABLE photo_requests ADD COLUMN agent_response_time_minutes INTEGER;"))
            print("  Columna 'agent_response_time_minutes' añadida.")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e):
                print("  Columna 'agent_response_time_minutes' ya existe.")
            else:
                print(f"  Error añadiendo 'agent_response_time_minutes': {e}")
                
        # Add csat_score
        try:
            conn.execute(text("ALTER TABLE photo_requests ADD COLUMN csat_score INTEGER;"))
            print("  Columna 'csat_score' añadida.")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e):
                print("  Columna 'csat_score' ya existe.")
            else:
                print(f"  Error añadiendo 'csat_score': {e}")
                
        # Add csat_feedback
        try:
            conn.execute(text("ALTER TABLE photo_requests ADD COLUMN csat_feedback TEXT;"))
            print("  Columna 'csat_feedback' añadida.")
        except Exception as e:
            if "Duplicate column name" in str(e) or "already exists" in str(e):
                print("  Columna 'csat_feedback' ya existe.")
            else:
                print(f"  Error añadiendo 'csat_feedback': {e}")

        print("Migración completada exitosamente.")

if __name__ == "__main__":
    migrate()
