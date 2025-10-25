from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"options": "-c client_encoding=UTF8"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Ensure uuid extension exists in Postgres
@event.listens_for(engine, "connect")
def ensure_extensions(dbapi_connection, connection_record):
    try:
        with dbapi_connection.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    except Exception:
        # If not Postgres, ignore.
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
