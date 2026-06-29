-- USERS
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- CATEGORIES (system defaults + user-custom)
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(50),
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    UNIQUE (user_id, name)
);

-- RAW SMS LOGS
CREATE TABLE sms_raw_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    sender_id VARCHAR(20),
    raw_text TEXT NOT NULL,
    received_at TIMESTAMP NOT NULL,
    parse_status VARCHAR(20) DEFAULT 'pending',
    parser_used VARCHAR(50),
    parse_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- TRANSACTIONS
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    sms_log_id INT,

    amount DECIMAL(12,2) NOT NULL,
    txn_type VARCHAR(10) NOT NULL,      -- debit | credit
    merchant_raw VARCHAR(255),
    merchant_clean VARCHAR(255),

    category_id INT,

    upi_app VARCHAR(30),
    app_label_source VARCHAR(20) DEFAULT 'unknown',
    app_label_confidence DECIMAL(4,3),

    source VARCHAR(10) NOT NULL,        -- sms | manual
    bank_ref_id VARCHAR(100),

    txn_timestamp TIMESTAMP NOT NULL,
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (sms_log_id)
        REFERENCES sms_raw_logs(id)
        ON DELETE SET NULL,

    FOREIGN KEY (category_id)
        REFERENCES categories(id),

    UNIQUE (user_id, bank_ref_id)
);

CREATE INDEX idx_txn_user_time
ON transactions(user_id, txn_timestamp DESC);

CREATE INDEX idx_txn_user_category
ON transactions(user_id, category_id);

-- MONTHLY SUMMARIES
CREATE TABLE monthly_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,

    year INT NOT NULL,
    month INT NOT NULL,

    total_spent DECIMAL(14,2) DEFAULT 0,
    total_credit DECIMAL(14,2) DEFAULT 0,

    category_breakdown JSON,
    app_breakdown JSON,
    source_breakdown JSON,

    txn_count INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    UNIQUE (user_id, year, month)
);

-- WEEKLY SUMMARIES
CREATE TABLE weekly_summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,

    week_start DATE NOT NULL,

    total_spent DECIMAL(14,2) DEFAULT 0,

    app_breakdown JSON,
    source_breakdown JSON,

    txn_count INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    UNIQUE (user_id, week_start)
);