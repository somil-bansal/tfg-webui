from peewee import PostgresqlDatabase
from peewee_migrate import Router
from config import SRC_LOG_LEVELS
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


log = logging.getLogger(__name__)

DB = PostgresqlDatabase(
    'postgres',  # the name of the database
    user='postgres',  # the username of your Postgres
    password='2Y7E0SLJx4F6qRg',  # the password for the Postgres user
    host='tfg-ai.cluster-cbc8jlxr7ybr.us-east-1.rds.amazonaws.com',  # the host for your PostgreSQL server
    port=5432,  # port for your PostgreSQL server
    autorollback=True,
    autocommit=False
)

log.info(f"Connected to a {DB.__class__.__name__} database.")
router = Router(DB, migrate_dir="apps/web/internal/migrations", logger=log)
router.run()
DB.connect(reuse_if_open=True)
