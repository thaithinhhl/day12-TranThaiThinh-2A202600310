from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    agent_api_key: str = Field(default="secret", alias="AGENT_API_KEY")
    llm_model: str = Field(default="mock-llm-v1", alias="LLM_MODEL")

    rate_limit_per_minute: int = Field(default=10, alias="RATE_LIMIT_PER_MINUTE")
    monthly_budget_usd: float = Field(default=10.0, alias="MONTHLY_BUDGET_USD")

    conversation_max_turns: int = Field(default=20, alias="CONVERSATION_MAX_TURNS")
    estimated_cost_per_request_usd: float = Field(
        default=0.01, alias="ESTIMATED_COST_PER_REQUEST_USD"
    )


settings = Settings()
