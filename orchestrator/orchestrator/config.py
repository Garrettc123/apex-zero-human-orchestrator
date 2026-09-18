from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Core
    environment: str = "production"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-prod"

    # Database
    database_url: str = "postgresql://apex_admin:password@localhost:5432/apexai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # GitHub
    github_token: Optional[str] = None
    github_org: str = "Garrettc123"
    github_default_private: bool = True

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # LLM / RHNS substrate
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Product factory
    product_catalog_path: str = "/app/catalog/PRODUCT_CATALOG.yaml"
    max_concurrent_products: int = 5
    auto_public_threshold_mrr: float = 10000.0  # only propose public after this simulated/actual MRR

    # Guardrails
    require_human_approval_for_public: bool = True
    require_human_approval_for_pricing: bool = True
    require_human_approval_for_capital: bool = True

    # Optimization loop
    optimization_interval_days: int = 14
    revenue_engine_interval_hours: int = 6

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
