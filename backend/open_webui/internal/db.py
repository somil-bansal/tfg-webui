import json
import logging
from contextlib import contextmanager
from typing import Any, Optional

from sqlalchemy import create_engine, MetaData, types, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from typing_extensions import Self

from the_finance_genie.env import (
    DATABASE_URL,
    DATABASE_SCHEMA,
    SRC_LOG_LEVELS,
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

def ensure_pgvector_extension():
    """Ensure pgvector extension is enabled in the database."""
    with get_db() as db:
        try:
            # Check if pgvector extension exists
            result = db.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            if not result.fetchone():
                log.info("Enabling pgvector extension...")
                db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                db.commit()
                log.info("pgvector extension enabled successfully")
            else:
                log.info("pgvector extension already enabled")
        except Exception as e:
            log.error(f"Error enabling pgvector extension: {e}")
            raise

class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[Any], dialect) -> Any:
        if value is not None:
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)

metadata_obj = MetaData(schema=DATABASE_SCHEMA)
Base = declarative_base(metadata=metadata_obj)

if DATABASE_POOL_SIZE > 0:
    engine = create_engine(
        DATABASE_URL,
        pool_size=DATABASE_POOL_SIZE,
        max_overflow=DATABASE_POOL_MAX_OVERFLOW,
        pool_timeout=DATABASE_POOL_TIMEOUT,
        pool_recycle=DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
        poolclass=QueuePool,
    )
else:
    engine = create_engine(
        DATABASE_URL, pool_pre_ping=True, poolclass=NullPool
    )

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)
Session = scoped_session(SessionLocal)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

ensure_pgvector_extension()
