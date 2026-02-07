from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_port: int = 8000

    postgres_dsn: str = "postgresql://rag:rag@localhost:5432/rag"

    qdrant_url: str = "http://localhost:6333"
    qdrant_grpc_port: int = 6334
    qdrant_collection: str = "rag_chunks"
    embedding_dim: int = 768

    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "rag_chunks"
    llm_gateway_url: str = "http://localhost:8004"
    query_api_url: str = "http://localhost:8001"

    top_k: int = 10
    bm25_k: int = 20
    vector_k: int = 20

    fusion_method: str = "rrf"
    rrf_k: int = 60
    bm25_weight: float = 0.4
    vector_weight: float = 0.6

    rerank_backend: str = "service"
    rerank_url: str = "http://localhost:8005"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_top_n: int = 10

    source_priority: str = ""

    rag_max_context_length: int = 4000
    rag_default_temperature: float = 0.3
    rag_max_tokens: int = 1024

    extraction_min_confidence: float = 0.7
    extraction_max_tokens: int = 1024
    extraction_temperature: float = 0.1

    cache_enabled: bool = True
    cache_ttl_search: int = 300
    cache_ttl_rag: int = 600
    cache_ttl_extraction: int = 1800
    redis_url: str = "redis://localhost:6379/0"

    hyde_enabled: bool = False
    hyde_max_length: int = 200
    hyde_temperature: float = 0.3

    query_decomposition_enabled: bool = False
    decomposition_max_subqueries: int = 3
    decomposition_merge_strategy: str = "rrf"

    query_cache_enabled: bool = True
    query_cache_ttl: int = 3600
    query_cache_max_size: int = 10000

    model_config = SettingsConfigDict(env_prefix="RAG_")


settings = Settings()
