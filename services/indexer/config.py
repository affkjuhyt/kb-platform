from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_port: int = 8000

    chunk_method: str = "sentence"  # sentence | semantic | markdown
    chunk_max_chars: int = 1200
    chunk_overlap_chars: int = 200
    chunk_min_chars: int = 200

    semantic_chunk_threshold: float = 0.7
    semantic_embedder_name: str = "intfloat/multilingual-e5-base"

    postgres_dsn: str = "postgresql://rag:rag@localhost:5432/rag"

    qdrant_url: str = "http://localhost:6333"
    qdrant_grpc_port: int = 6334
    qdrant_collection: str = "rag_chunks"
    embedding_dim: int = 384
    embedding_backend: str = "sentence-transformers"
    embedding_model: str = "intfloat/multilingual-e5-base"

    embedding_batch_size: int = 32
    embedding_num_workers: int = 4

    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "rag_chunks"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "raw-docs"
    minio_secure: bool = False

    kafka_brokers: str = "localhost:9092"
    kafka_ingestion_topic: str = "ingestion.events"
    kafka_chunk_topic: str = "indexer.chunks"
    chunk_schema_version: int = 1

    model_config = SettingsConfigDict(env_prefix="RAG_")


settings = Settings()
