-- ==========================================
-- CLIENTS
-- ==========================================

CREATE TABLE clients (

    client_id SERIAL PRIMARY KEY,

    client_name VARCHAR(200) NOT NULL,

    industry VARCHAR(100),

    contact_person VARCHAR(150),

    email VARCHAR(150),

    phone VARCHAR(20),

    country VARCHAR(100),

    status VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- CONTRACTS
-- ==========================================

CREATE TABLE contracts (

    contract_id SERIAL PRIMARY KEY,

    client_id INTEGER NOT NULL,

    contract_number VARCHAR(50) UNIQUE,

    contract_title VARCHAR(200),

    start_date DATE,

    end_date DATE,

    contract_value DECIMAL(15,2),

    status VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_contract_client
        FOREIGN KEY(client_id)
        REFERENCES clients(client_id)
);

-- ==========================================
-- ADD PROJECT -> CLIENT RELATION
-- ==========================================

ALTER TABLE projects
ADD CONSTRAINT fk_project_client
FOREIGN KEY (client_id)
REFERENCES clients(client_id);