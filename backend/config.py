import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    PROJECT_NAME: str = "SRE-Shield"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-Powered Self-Learning Incident Response Agent with Hindsight Memory"

    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    FALLBACK_MODEL: str = "llama-3.1-8b-instant"

    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite+aiosqlite:///{DATA_DIR / 'sre_shield.db'}"
    )
    # Sync database URL for sync utilities / migrations
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        f"sqlite:///{DATA_DIR / 'sre_shield.db'}"
    )

    # Hindsight Agent Memory Settings
    HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")
    HINDSIGHT_ENDPOINT: str = os.getenv("HINDSIGHT_ENDPOINT", "https://api.hindsight.vectorize.io/v1")
    HINDSIGHT_BANK_NAME: str = os.getenv("HINDSIGHT_BANK_NAME", "sre-shield-production")

    # API & Frontend Ports
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))

    # Execution Mode
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "true").lower() in ("true", "1", "yes")

settings = Settings()
