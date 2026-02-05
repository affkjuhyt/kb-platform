from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_port: int = 8000

    postgres_dsn: str = "postgresql://rag:rag@localhost:5432/rag"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "raw-docs"
    minio_secure: bool = False

    kafka_brokers: str = "localhost:9092"
    kafka_topic: str = "ingestion.events"

    model_config = SettingsConfigDict(env_prefix="RAG_")


settings = Settings()
