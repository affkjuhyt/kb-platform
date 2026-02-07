from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_port: int = 8000
    model: str = "ms-marco-MiniLM-L-12-v2"
    device: str = "cpu"
    max_batch: int = 16
    top_k: int = 10  # Rerank top-k candidates
    normalize_scores: bool = True  # Normalize scores to [0, 1]

    model_config = SettingsConfigDict(env_prefix="RAG_")


settings = Settings()
