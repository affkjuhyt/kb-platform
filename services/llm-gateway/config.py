from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_port: int = 8000
    llm_backend: str = "ollama"  # ollama | mock
    ollama_host: str = "http://host.docker.internal:11434"
    model: str = "llama3.1:8b-instruct"
    model_config = SettingsConfigDict(env_prefix="RAG_")


settings = Settings()
