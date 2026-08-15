import logging
from sqlalchemy import create_engine
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

# Qdrant Vector Client
def get_qdrant_client() -> QdrantClient:
    """Return Qdrant Vector DB client instance."""
    try:
        client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise e

# Neo4j Graph DB Connection
def get_neo4j_driver():
    """Neo4j driver context dependency."""
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        return driver
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise e

# Redis Caching Connection
def get_redis_client():
    """Return Redis client instance."""
    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise e
