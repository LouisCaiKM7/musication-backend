import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env as early as possible so os.getenv picks them up
load_dotenv()

@dataclass
class Settings:
    flask_env: str = os.getenv("FLASK_ENV", "development")
    port: int = int(os.getenv("PORT", "8000"))
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/musication",
    )
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")

settings = Settings()
