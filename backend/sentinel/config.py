from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./sentinel.db"
    redis_url: str = "redis://redis:6379/0"
    api_token: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    sync_jobs: bool = False

settings = Settings()
