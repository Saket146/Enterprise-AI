import logging
import threading
from typing import Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
import redis
from app.configuration.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for models
Base = declarative_base()

# PostgreSQL Connection
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """PostgreSQL session generator dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# The three optional stores below are created once and shared.  Creating a
# client does not open a connection, so this never fails when a service is
# not installed or not running - callers handle the error on first use.
_lock = threading.Lock()
_qdrant_client = None
_neo4j_driver = None
_redis_client = None

# Qdrant Vector Client
def get_qdrant_client() -> QdrantClient:
    """Return the shared Qdrant Vector DB client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        with _lock:
            if _qdrant_client is None:
                try:
                    _qdrant_client = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                        timeout=10,
                        check_compatibility=False
                    )
                except Exception as e:
                    logger.error(f"Failed to create Qdrant client: {e}")
                    raise e
    return _qdrant_client

# Neo4j Graph DB Connection
def get_neo4j_driver():
    """Return the shared Neo4j driver. Do not close it - it is reused across requests."""
    global _neo4j_driver
    if _neo4j_driver is None:
        with _lock:
            if _neo4j_driver is None:
                try:
                    _neo4j_driver = GraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                        connection_timeout=5,
                        connection_acquisition_timeout=10,
                        max_transaction_retry_time=5
                    )
                except Exception as e:
                    logger.error(f"Failed to create Neo4j driver: {e}")
                    raise e
    return _neo4j_driver

# Redis Caching Connection
def get_redis_client():
    """Return the shared Redis client instance."""
    global _redis_client
    if _redis_client is None:
        with _lock:
            if _redis_client is None:
                try:
                    _redis_client = redis.Redis(
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT,
                        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=3
                    )
                except Exception as e:
                    logger.error(f"Failed to create Redis client: {e}")
                    raise e
    return _redis_client


def check_dependencies() -> Dict[str, Dict[str, str]]:
    """
    Probe the four data stores and report which are reachable.
    PostgreSQL is required; Redis, Qdrant and Neo4j are optional - the
    application falls back gracefully when they are offline.
    """
    report: Dict[str, Dict[str, str]] = {}

    def probe(name: str, required: bool, fn):
        try:
            fn()
            report[name] = {"status": "online", "required": str(required).lower()}
        except Exception as e:
            report[name] = {
                "status": "offline",
                "required": str(required).lower(),
                "error": str(e).splitlines()[0][:200] if str(e) else type(e).__name__,
            }

    def _postgres():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    probe("postgresql", True, _postgres)
    probe("redis", False, lambda: get_redis_client().ping())
    probe("qdrant", False, lambda: get_qdrant_client().get_collections())
    probe("neo4j", False, lambda: get_neo4j_driver().verify_connectivity())
    return report
