from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


database_url = settings.DATABASE_URL

connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}  # Solo SQLite

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency que provee una sesión de DB por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
