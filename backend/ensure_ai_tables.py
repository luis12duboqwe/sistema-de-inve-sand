from app.database import engine, Base
from app.models import Customer, AIProfileConfig, InteractionLog, TrainingQueue

def create_tables():
    print("🔄 Checking and creating AI tables...")
    try:
        # This will create tables only if they don't exist
        Base.metadata.create_all(bind=engine)
        print("✅ Tables verified/created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
