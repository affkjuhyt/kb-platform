import os


class Settings:
    SERVICE_PORT = int(os.getenv("API_GATEWAY_PORT", "8000"))
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here").strip("\"'")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # Rate limiting
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5432/rag")

    # Backend services
    QUERY_API_URL = os.getenv("QUERY_API_URL", "http://localhost:8001")
    LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8004")
    INGESTION_API_URL = os.getenv("INGESTION_API_URL", "http://localhost:8002")

    # Audit logging
    AUDIT_LOG_ENABLED = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"


settings = Settings()
