from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_port: int = 8000
    llm_backend: str = "ollama"
    llm_provider: str = "ollama"

    ollama_host: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b-instruct"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_base_url: str = "https://api.anthropic.com"

    default_max_tokens: int = 1024
    default_temperature: float = 0.3

    model_config = SettingsConfigDict(env_prefix="LLM_")


settings = Settings()


def get_model_for_provider(provider: str) -> str:
    """Get the appropriate model name based on provider."""
    if provider == "openai":
        return settings.openai_model
    elif provider == "anthropic":
        return settings.anthropic_model
    elif provider == "ollama":
        return settings.ollama_model
    return settings.ollama_model


def get_api_key_for_provider(provider: str) -> str:
    """Get API key for provider."""
    if provider == "openai":
        return settings.openai_api_key
    elif provider == "anthropic":
        return settings.anthropic_api_key
    return ""
