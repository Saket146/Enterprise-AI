# scripts/seed_data.py
# Python script to seed the PostgreSQL database with generated synthetic data.

import os
import sys
import psycopg2
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
SEED_PATH = os.path.join(BASE_DIR, "synthetic_data", "postgres", "seed_data.sql")

def run_seed():
    """Execute SQL statements from seed_data.sql."""
    if not os.path.exists(SEED_PATH):
        print(f"Seed SQL file not found at: {SEED_PATH}", file=sys.stderr)
        print("Please run 'python scripts/generate_data.py' first to generate seed data.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Reading seed SQL from: {SEED_PATH}...")
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        seed_sql = f.read()
        
    print(f"Connecting to database '{DB_NAME}' at {DB_HOST}:{DB_PORT} to run seeds...")
    try:
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        cursor = conn.cursor()
        print("Running SQL inserts (this might take a few moments for 1000+ employees)...")
        cursor.execute(seed_sql)
        conn.commit()
        print("Database seeded successfully with synthetic enterprise records!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error seeding database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_seed()
