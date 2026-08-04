# scripts/build_graph.py
# Python script to load the synthetic enterprise graph into Neo4j using Cypher queries.

import os
import sys
from dotenv import load_dotenv

# Load env variables from backend/.env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")
load_dotenv(ENV_PATH)

# Fetch settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "password")
CYPHER_PATH = os.path.join(BASE_DIR, "synthetic_data", "neo4j", "import_graph.cypher")

def main():
    # Attempt to import neo4j driver
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("\n[ERROR] The 'neo4j' Python driver is not installed.", file=sys.stderr)
        print("Please install it using your virtual environment pip:", file=sys.stderr)
        print("    pip install neo4j\n", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(CYPHER_PATH):
        print(f"[ERROR] Cypher seed file not found at: {CYPHER_PATH}", file=sys.stderr)
        print("Please run 'python scripts/generate_data.py' first.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading Cypher statements from: {CYPHER_PATH}...")
    with open(CYPHER_PATH, "r", encoding="utf-8") as f:
        cypher_content = f.read()

    # Split cypher commands by semicolon (filtering comments and empty statements)
    statements = []
    for stmt in cypher_content.split(";"):
        stmt_clean = stmt.strip()
        if stmt_clean and not stmt_clean.startswith("//"):
            statements.append(stmt_clean)

    print(f"Connecting to Neo4j database at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            print(f"Running {len(statements)} Cypher transactions...")
            for idx, stmt in enumerate(statements):
                try:
                    # Run statement in write transaction
                    session.run(stmt)
                except Exception as ex:
                    print(f"Warning: Failed to execute statement {idx+1}: {stmt[:100]}...\nReason: {ex}")
            print("\nNeo4j enterprise knowledge graph built successfully!")
        driver.close()
    except Exception as e:
        print(f"[ERROR] Failed to connect or execute queries on Neo4j: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
