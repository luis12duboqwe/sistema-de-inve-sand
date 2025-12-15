-- Crear tabla Customers
CREATE TABLE IF NOT EXISTS customers (
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

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_customers_troll ON customers(is_troll);

-- Crear tabla AIProfileConfig
CREATE TABLE IF NOT EXISTS ai_profile_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_profile_id INTEGER NOT NULL UNIQUE,
    model_name VARCHAR DEFAULT 'gpt-4o',
    temperature FLOAT DEFAULT 0.7,
    system_prompt TEXT NOT NULL,
    initial_greeting TEXT,
    voice_tone VARCHAR,
    context_rules TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sales_profile_id) REFERENCES sales_profiles(id) ON DELETE CASCADE
);

-- Crear tabla InteractionLogs
CREATE TABLE IF NOT EXISTS interaction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    sales_profile_id INTEGER NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    converted_order_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY(sales_profile_id) REFERENCES sales_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY(converted_order_id) REFERENCES orders(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_interactions_customer ON interaction_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_interactions_profile ON interaction_logs(sales_profile_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON interaction_logs(created_at);

-- Crear tabla TrainingQueue
CREATE TABLE IF NOT EXISTS training_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_profile_id INTEGER,
    customer_question TEXT NOT NULL,
    ai_proposed_answer TEXT,
    admin_correction TEXT,
    status VARCHAR DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sales_profile_id) REFERENCES sales_profiles(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_training_status ON training_queue(status);
