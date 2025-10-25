import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env as early as possible so os.getenv picks them up
load_dotenv()

@dataclass
class Settings:
    flask_env: str = os.getenv("FLASK_ENV", "development")
    port: int = int(os.getenv("PORT", "8000"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    
    @property
    def database_url(self) -> str:
        """
        Get DATABASE_URL and ensure it uses psycopg v3 driver.
        Render provides postgresql:// which defaults to psycopg2 (old),
        so we replace it with postgresql+psycopg:// for psycopg v3.
        """
        url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/musication",
        )
        # Render/Heroku provide postgresql:// - convert to postgresql+psycopg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

settings = Settings()

