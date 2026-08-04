# scripts/create_embeddings.py
# Python script to initialize Qdrant collections according to the metadata schema specifications.

import os
import sys
import json
from dotenv import load_dotenv

# Load env variables from backend/.env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")
load_dotenv(ENV_PATH)

# Fetch settings
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
SCHEMA_PATH = os.path.join(BASE_DIR, "synthetic_data", "qdrant", "collections_schema.json")

def main():
    # Attempt to import Qdrant client
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels
    except ImportError:
        print("\n[ERROR] The 'qdrant-client' Python package is not installed.", file=sys.stderr)
        print("Please install it using your virtual environment pip:", file=sys.stderr)
        print("    pip install qdrant-client\n", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(SCHEMA_PATH):
        print(f"[ERROR] Schema configuration not found at: {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading collections schema from: {SCHEMA_PATH}...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    try:
        client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
        )
        
        # Verify connection
        client.get_collections()
        print("Connected successfully to Qdrant.")
        
        for coll in schema_data.get("collections", []):
            name = coll["name"]
            vec_config = coll["vector_config"]
            size = vec_config["size"]
            distance_str = vec_config["distance"]
            
            # Map distance string to Qdrant SDK model distance
            distance = qmodels.Distance.COSINE
            if distance_str.upper() == "EUCLIDEAN":
                distance = qmodels.Distance.EUCLID
            elif distance_str.upper() == "DOT":
                distance = qmodels.Distance.DOT
                
            print(f"Checking collection '{name}'...")
            
            # Recreate or create collection
            try:
                # If collection exists, we can log it. Otherwise we create it
                exists = False
                collections_res = client.get_collections()
                for c in collections_res.collections:
                    if c.name == name:
                        exists = True
                        break
                        
                if exists:
                    print(f"Collection '{name}' already exists. Re-configuring (recreating)...")
                    client.recreate_collection(
                        collection_name=name,
                        vectors_config=qmodels.VectorParams(
                            size=size,
                            distance=distance
                        )
                    )
                else:
                    print(f"Creating collection '{name}'...")
                    client.create_collection(
                        collection_name=name,
                        vectors_config=qmodels.VectorParams(
                            size=size,
                            distance=distance
                        )
                    )
                print(f"Collection '{name}' initialized successfully (Vector size: {size}, Metric: {distance_str}).")
            except Exception as coll_err:
                print(f"Failed to configure collection '{name}': {coll_err}", file=sys.stderr)
                
        print("\nAll Qdrant collections initialized successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Qdrant instance: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
