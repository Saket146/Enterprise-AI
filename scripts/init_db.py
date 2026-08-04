# scripts/init_db.py
# Python script to initialize the PostgreSQL database schema.

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load env variables from backend/.env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")
load_dotenv(ENV_PATH)

# Fetch settings
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "enterprise_ai_os")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
SCHEMA_PATH = os.path.join(BASE_DIR, "synthetic_data", "postgres", "schema.sql")

def create_database():
    """Ensure the target database exists."""
    print(f"Connecting to default postgres database on {DB_HOST}:{DB_PORT} to verify '{DB_NAME}' exists...")
    try:
        # Connect to 'postgres' default database to check/create the target database
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}';")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{DB_NAME}' not found. Creating database...")
            cursor.execute(f"CREATE DATABASE {DB_NAME};")
            print(f"Database '{DB_NAME}' created successfully.")
        else:
            print(f"Database '{DB_NAME}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}", file=sys.stderr)
        sys.exit(1)

def run_schema():
    """Execute DDL statements from schema.sql."""
    if not os.path.exists(SCHEMA_PATH):
        print(f"Schema file not found at: {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Reading DDL schema from: {SCHEMA_PATH}...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    print(f"Connecting to database '{DB_NAME}' at {DB_HOST}:{DB_PORT}...")
    try:
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        cursor = conn.cursor()
        print("Executing DDL statements...")
        cursor.execute(schema_sql)
        conn.commit()
        print("Database schema initialized successfully.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error executing DDL schema: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    create_database()
    run_schema()
