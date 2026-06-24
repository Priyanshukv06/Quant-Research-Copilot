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

    # ── NVIDIA NIM (Primary LLM) ──
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "google/diffusiongemma-26b-a4b-it")

    # ── Groq (Cloud Fallback) ──
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ── BigQuery ──
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "adk-mini-project")
    GCP_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "GCP_SERVICE_ACCOUNT_PATH",
        str(Path(__file__).parent.parent.parent / "Quantamental_SwingTrading_Strategy" / "service-account" / "service_account.json")
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
    TEMPERATURE: float = 0.3  # Lower for more deterministic slot-filling
    TOP_P: float = 0.95


settings = Settings()
