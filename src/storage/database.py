from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config.settings import get_settings

Base = declarative_base()


class DatabaseManager:
    """Manages database connections, schema initialization, and sessions."""

    def __init__(self, database_url: str | None = None):
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        
        # SQLite vs PostgreSQL connection argument configuration
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            if ":memory:" in self.database_url:
                from sqlalchemy.pool import StaticPool
                self.engine = create_engine(
                    self.database_url,
                    connect_args=connect_args,
                    poolclass=StaticPool,
                )
            else:
                self.engine = create_engine(self.database_url, connect_args=connect_args)
        else:
            self.engine = create_engine(
                self.database_url,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,
            )

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def init_schema(self, schema_file: Path | None = None) -> None:
        """Execute DDL statements from schema.sql."""
        sf = schema_file or (Path(__file__).parent / "schema.sql")
        if not sf.exists():
            return

        ddl_script = sf.read_text(encoding="utf-8")
        # For SQLite compatibility, replace SERIAL with INTEGER PRIMARY KEY AUTOINCREMENT
        if self.database_url.startswith("sqlite"):
            ddl_script = ddl_script.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            ddl_script = ddl_script.replace("TIMESTAMP WITHOUT TIME ZONE", "DATETIME")
            # SQLite supports DEFAULT CURRENT_TIMESTAMP directly, so no need to replace it

        statements = [stmt.strip() for stmt in ddl_script.split(";") if stmt.strip()]
        with self.engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global default DB instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Generator[Session, None, None]:
    manager = get_db_manager()
    with manager.get_session() as session:
        yield session
