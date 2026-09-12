"""
Centralized configuration loaded from .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Application settings from environment variables."""

    # ── BigQuery ──
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "adk-mini-project")
    GCP_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "GCP_SERVICE_ACCOUNT_PATH",
        "D:/Projects/Quantamental_SwingTrading_Strategy/service-account/service-account.json"
    )
    BQ_DATASET_FUNDAMENTALS: str = os.getenv("BQ_DATASET_FUNDAMENTALS", "adk-mini-project.fundamentals")
    BQ_DATASET_TECHNICALS: str = os.getenv("BQ_DATASET_TECHNICALS", "adk-mini-project.technicals")
    BQ_DATASET_EARNINGS: str = os.getenv("BQ_DATASET_EARNINGS", "adk-mini-project.earnings")
    BQ_DATASET_STOCKS: str = os.getenv("BQ_DATASET_STOCKS", "adk-mini-project.stocks")

    # ── Server ──
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ── LLM Settings ──
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.3      # Lower for more deterministic slot-filling
    TOP_P: float = 0.95
    LLM_TIMEOUT_SECONDS: int = 120

    # ── News Sources ──
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")
    NEWSDATA_API_KEY: str = os.getenv("NEWSDATA_API_KEY", "")
    NEWS_CACHE_TTL_SECONDS: int = int(os.getenv("NEWS_CACHE_TTL_SECONDS", "900"))

    # ── Router ──
    ROUTER_MAX_ATTEMPTS: int = 5
    ROUTER_ROTATE_KEYS: bool = True        # Failover: retry same model on next key
    ROUTER_ROUND_ROBIN_KEYS: bool = True   # Load balance: advance key after success
    ROUTER_RATE_LIMIT_COOLDOWN_S: int = 45
    ROUTER_SERVER_ERROR_COOLDOWN_S: int = 20
    ROUTER_AUTH_FAILURE_COOLDOWN_S: int = 3600


settings = Settings()
