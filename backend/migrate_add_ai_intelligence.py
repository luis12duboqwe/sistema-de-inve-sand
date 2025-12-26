import logging
from sqlalchemy import create_engine, text, inspect
from app.config import settings
from app.database import Base

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """
    Migración para agregar el módulo de Inteligencia Artificial (AI Intelligence Module).
    Agrega tablas para:
    1. Configuración avanzada de Bots (AIProfileConfig)
    2. Gestión de Clientes (Customer)
    3. Historial de Interacciones (InteractionLog)
    4. Cola de Aprendizaje (TrainingQueue)
    """
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    with engine.connect() as connection:
        # 1. Tabla Customers (Clientes)
        if not inspector.has_table("customers"):
            logger.info("Creando tabla 'customers'...")
            connection.execute(text("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number VARCHAR NOT NULL UNIQUE,
                name VARCHAR,
                email VARCHAR,
                notes TEXT,
                is_troll BOOLEAN DEFAULT 0,
                is_blocked BOOLEAN DEFAULT 0,
                reputation_score INTEGER DEFAULT 100,
                daily_message_count INTEGER DEFAULT 0,
                last_interaction_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """))
            connection.execute(text("CREATE INDEX idx_customers_phone ON customers(phone_number);"))
            connection.execute(text("CREATE INDEX idx_customers_troll ON customers(is_troll);"))
        else:
            logger.info("Tabla 'customers' ya existe.")

        # 2. Tabla AIProfileConfig (Configuración de IA por Perfil de Venta)
        if not inspector.has_table("ai_profile_configs"):
            logger.info("Creando tabla 'ai_profile_configs'...")
            connection.execute(text("""
            CREATE TABLE ai_profile_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_profile_id INTEGER NOT NULL UNIQUE,
                model_name VARCHAR DEFAULT 'gpt-4o',
                temperature FLOAT DEFAULT 0.7,
                system_prompt TEXT NOT NULL,
                initial_greeting TEXT,
                context_rules TEXT, -- JSON: Filtros de inventario, categorías permitidas
                voice_tone VARCHAR, -- 'formal', 'amigable', 'agresivo', 'sarcastico'
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(sales_profile_id) REFERENCES sales_profiles(id) ON DELETE CASCADE
            );
            """))
        else:
            logger.info("Tabla 'ai_profile_configs' ya existe.")

        # 3. Tabla InteractionLogs (Historial de Chats)
        if not inspector.has_table("interaction_logs"):
            logger.info("Creando tabla 'interaction_logs'...")
            connection.execute(text("""
            CREATE TABLE interaction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                sales_profile_id INTEGER NOT NULL,
                role VARCHAR NOT NULL, -- 'user', 'assistant', 'system'
                content TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                converted_order_id INTEGER, -- Si este mensaje llevó a una venta
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY(sales_profile_id) REFERENCES sales_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY(converted_order_id) REFERENCES orders(id) ON DELETE SET NULL
            );
            """))
            connection.execute(text("CREATE INDEX idx_interactions_customer ON interaction_logs(customer_id);"))
            connection.execute(text("CREATE INDEX idx_interactions_profile ON interaction_logs(sales_profile_id);"))
            connection.execute(text("CREATE INDEX idx_interactions_created ON interaction_logs(created_at);"))
        else:
            logger.info("Tabla 'interaction_logs' ya existe.")

        # 4. Tabla TrainingQueue (Cola de Aprendizaje / Human-in-the-loop)
        if not inspector.has_table("training_queue"):
            logger.info("Creando tabla 'training_queue'...")
            connection.execute(text("""
            CREATE TABLE training_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_profile_id INTEGER,
                customer_question TEXT NOT NULL,
                ai_proposed_answer TEXT,
                admin_correction TEXT,
                status VARCHAR DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'converted_to_faq'
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(sales_profile_id) REFERENCES sales_profiles(id) ON DELETE SET NULL
            );
            """))
            connection.execute(text("CREATE INDEX idx_training_status ON training_queue(status);"))
        else:
            logger.info("Tabla 'training_queue' ya existe.")

        logger.info("Migración de Módulo IA completada exitosamente.")

if __name__ == "__main__":
    try:
        run_migration()
        print("✅ Migración completada correctamente.")
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
