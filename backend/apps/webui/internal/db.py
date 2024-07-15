import os
import logging
import json

from peewee import *
from peewee_migrate import Router

from apps.webui.internal.wrappers import register_connection
from config import SRC_LOG_LEVELS, DATA_DIR, BACKEND_DIR

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


DB = PostgresqlDatabase(
    'postgres',  # the name of the database
    user='postgres',  # the username of your Postgres
    # password='2Y7E0SLJx4F6qRg',  # the password for the Postgres user web
    password='''E!DA4S42QswiXyaRzXOcEb_$|wi+''',  # the password for the Postgres user tfg
    # host='tfg-ai.cluster-cbc8jlxr7ybr.us-east-1.rds.amazonaws.com',  # the host for your PostgreSQL server web
    host='the-finance-genie-psql.cluster-cuoiovlnzgsd.us-east-1.rds.amazonaws.com',  # the host for your PostgreSQL server tfg
    port=5432,  # port for your PostgreSQL server
    autorollback=True,
    autocommit=False
)

log.info(f"Connected to a {DB.__class__.__name__} database.")
router = Router(
    DB,
    migrate_dir=BACKEND_DIR / "apps" / "webui" / "internal" / "migrations",
    logger=log,
)
router.run()
try:
    DB.connect(reuse_if_open=True)
except OperationalError as e:
    log.info(f"Failed to connect to database again due to: {e}")
    pass
