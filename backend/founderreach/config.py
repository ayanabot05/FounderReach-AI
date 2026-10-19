import os
from pathlib import Path

# Settings use the process environment.
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    # Project Info
    PROJECT_NAME: str = "FounderReach AI"
    VERSION: str = "2.5.0"
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    DB_PATH: Path = DATA_DIR / "founderreach.db"
    
    # Admin Credentials (Configured in .env)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@founderreach.ai")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123456")
    
    # Security & Auth
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "founderreach-saas-jwt-secret-key-prod-2026")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = 7
    
    # Rate Limiting & Caching
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "900")) # 15 minutes default
    
    # Financial Controls & Payments (Stripe)
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    BUDGET_TARGET_INR: float = float(os.getenv("BUDGET_TARGET_INR", "600.00"))
    BUDGET_CEILING_INR: float = float(os.getenv("BUDGET_HARD_CEILING_INR", "1000.00"))
    AUTHORIZED_NEW_SPEND_INR: float = 0.0
    
    # Database Configuration (Supabase & SQLite)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_ENABLED: bool = os.getenv("SUPABASE_ENABLED", "false").lower() in ("true", "1", "yes")
    
    # Source Connectors
    HN_ENABLED: bool = os.getenv("HN_ENABLED", "true").lower() in ("true", "1", "yes")
    HN_API_BASE: str = os.getenv("HN_API_BASE", "https://hn.algolia.com/api/v1")
    
    # Reddit Connector
    REDDIT_ENABLED: bool = os.getenv("REDDIT_ENABLED", "false").lower() in ("true", "1", "yes")
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "FounderReach/2.5")
    
    # AI / LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Opportunity Thresholds
    DEFAULT_SCORE_THRESHOLD: int = int(os.getenv("DEFAULT_SCORE_THRESHOLD", "75"))

settings = Settings()
