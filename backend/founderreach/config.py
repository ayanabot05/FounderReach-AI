import os
from pathlib import Path

# Settings use the process environment. Importing this module must never read
# a credential file; an authorized operator can populate the environment first.
BASE_DIR = Path(__file__).resolve().parent.parent

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
    # Current CEO authorization. Historical budget targets do not authorize spending.
    AUTHORIZED_NEW_SPEND_INR: float = 0.0
    
    # Cloud Database disabled in local-only mode (M1 uses local SQLite ResearchStore)
    SUPABASE_ENABLED: bool = False
    
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

