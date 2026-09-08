from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import get_settings

settings = get_settings()

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def ensure_schema():
    """
    Apply lightweight, idempotent schema updates.

    The project does not currently use Alembic migrations, so this handles
    additive schema changes for existing databases.
    """
    inspector = inspect(engine)

    if "pr_analysis" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("pr_analysis")
    }

    if "change_graph" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE pr_analysis "
                    "ADD COLUMN change_graph TEXT"
                )
            )


def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()