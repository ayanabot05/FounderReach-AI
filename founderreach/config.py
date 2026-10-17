import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # Project Info
    PROJECT_NAME: str = "FounderReach AI"
    VERSION: str = "1.0.0"
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    DB_PATH: Path = DATA_DIR / "founderreach.db"
    
    # Financial Controls (INR)
    BUDGET_TARGET_INR: float = float(os.getenv("BUDGET_TARGET_INR", "600.00"))
    BUDGET_CEILING_INR: float = float(os.getenv("BUDGET_HARD_CEILING_INR", "1000.00"))
    
    # Supabase Cloud Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xsumvcqeqknshjwdnypy.supabase.co")
    # Database access is server-only. Never silently use an anon key with broad RLS.
    SUPABASE_KEY: str = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Source Connectors
    HN_ENABLED: bool = os.getenv("HN_ENABLED", "true").lower() in ("true", "1", "yes")
    HN_API_BASE: str = os.getenv("HN_API_BASE", "https://hn.algolia.com/api/v1")
    
    # Reddit is explicitly disabled by default per CEO directive
    REDDIT_ENABLED: bool = os.getenv("REDDIT_ENABLED", "false").lower() in ("true", "1", "yes")
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "FounderReach/1.0")
    
    # AI / LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Default minimum score threshold for customer opportunities
    DEFAULT_SCORE_THRESHOLD: int = int(os.getenv("DEFAULT_SCORE_THRESHOLD", "75"))

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
