from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_max_tokens: int = 4096
    anthropic_timeout_seconds: int = 60

    max_requests_per_site: int = 10
    rate_limit_ttl_hours: int = 24

    allowed_origins: str = "*"

    model_config = {"env_file": ".env"}


settings = Settings()
