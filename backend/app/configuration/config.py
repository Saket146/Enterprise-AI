import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise AI Operating System"
    PROJECT_VERSION: str = "3.0.0"
    DEBUG: bool = False

    # PostgreSQL Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "enterprise_ai_os"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/enterprise_ai_os"

    # Qdrant Vector DB Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""

    # Neo4j Graph Database Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Redis Caching Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # LLM Settings
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "mock"  # Options: 'gemini', 'openai', 'mock'
    # Gemini model to use, e.g. gemini-2.5-flash. Leave empty to use the newest stable Flash model.
    GEMINI_MODEL: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # JWT Settings
    JWT_SECRET_KEY: str = "enterprise_ai_os_secret_key_very_secure_change_me_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Folder of the built website (frontend `npm run build`). Empty: found automatically.
    FRONTEND_DIST: str = ""
    API_KEY_HEADER: str = "X-Enterprise-API-Key"
    ENTERPRISE_API_KEY: str = ""
    MAX_REQUEST_BYTES: int = 1_048_576
    SENSITIVE_DATA_MASKING: bool = True

    class Config:
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env"
        )
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
