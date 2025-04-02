import json
import logging
import os
import shutil
import base64
import redis

from datetime import datetime
from pathlib import Path
from typing import Generic, Optional, TypeVar
from urllib.parse import urlparse

import requests
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, func

from the_finance_genie.env import (
    DATA_DIR,
    DATABASE_URL,
    ENV,
    REDIS_URL,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_PORT,
    FRONTEND_BUILD_DIR,
    OFFLINE_MODE,
    OPEN_WEBUI_DIR,
    WEBUI_AUTH,
    WEBUI_FAVICON_URL,
    WEBUI_NAME,
    log,
)
from the_finance_genie.internal.db import Base, get_db
from the_finance_genie.utils.redis import get_redis_connection


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

####################################
# Config helpers
####################################


# Function to run the alembic migrations
def run_migrations():
    log.info("Running migrations")
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(OPEN_WEBUI_DIR / "alembic.ini")

        # Set the script location dynamically
        migrations_path = OPEN_WEBUI_DIR / "migrations"
        alembic_cfg.set_main_option("script_location", str(migrations_path))

        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        log.exception(f"Error running migrations: {e}")


run_migrations()


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    data = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


def load_json_config():
    with open(f"{DATA_DIR}/config.json", "r") as file:
        return json.load(file)


def save_to_db(data):
    with get_db() as db:
        existing_config = db.query(Config).first()
        if not existing_config:
            new_config = Config(data=data, version=0)
            db.add(new_config)
        else:
            existing_config.data = data
            existing_config.updated_at = datetime.now()
            db.add(existing_config)
        db.commit()


def reset_config():
    with get_db() as db:
        db.query(Config).delete()
        db.commit()


# When initializing, check if config.json exists and migrate it to the database
if os.path.exists(f"{DATA_DIR}/config.json"):
    data = load_json_config()
    save_to_db(data)
    os.rename(f"{DATA_DIR}/config.json", f"{DATA_DIR}/old_config.json")

DEFAULT_CONFIG = {
    "version": 0,
    "ui": {
        "default_locale": "",
        "prompt_suggestions": [
            {
                "title": [
                    "Help me study",
                    "vocabulary for a college entrance exam",
                ],
                "content": "Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option.",
            },
            {
                "title": [
                    "Give me ideas",
                    "for what to do with my kids' art",
                ],
                "content": "What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter.",
            },
            {
                "title": ["Tell me a fun fact", "about the Roman Empire"],
                "content": "Tell me a random fun fact about the Roman Empire",
            },
            {
                "title": [
                    "Show me a code snippet",
                    "of a website's sticky header",
                ],
                "content": "Show me a code snippet of a website's sticky header in CSS and JavaScript.",
            },
            {
                "title": [
                    "Explain options trading",
                    "if I'm familiar with buying and selling stocks",
                ],
                "content": "Explain options trading in simple terms if I'm familiar with buying and selling stocks.",
            },
            {
                "title": ["Overcome procrastination", "give me tips"],
                "content": "Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?",
            },
            {
                "title": [
                    "Grammar check",
                    "rewrite it for better readability ",
                ],
                "content": 'Check the following sentence for grammar and clarity: "[sentence]". Rewrite it for better readability while maintaining its original meaning.',
            },
        ],
    },
}


def get_config():
    with get_db() as db:
        config_entry = db.query(Config).order_by(Config.id.desc()).first()
        return config_entry.data if config_entry else DEFAULT_CONFIG


CONFIG_DATA = get_config()


def get_config_value(config_path: str):
    path_parts = config_path.split(".")
    cur_config = CONFIG_DATA
    for key in path_parts:
        if key in cur_config:
            cur_config = cur_config[key]
        else:
            return None
    return cur_config


PERSISTENT_CONFIG_REGISTRY = []


def save_config(config):
    global CONFIG_DATA
    global PERSISTENT_CONFIG_REGISTRY
    try:
        save_to_db(config)
        CONFIG_DATA = config

        # Trigger updates on all registered PersistentConfig entries
        for config_item in PERSISTENT_CONFIG_REGISTRY:
            config_item.update()
    except Exception as e:
        log.exception(e)
        return False
    return True


T = TypeVar("T")


class PersistentConfig(Generic[T]):
    def __init__(self, env_name: str, config_path: str, env_value: T):
        self.env_name = env_name
        self.config_path = config_path
        self.env_value = env_value
        self.config_value = get_config_value(config_path)
        if self.config_value is not None:
            log.info(f"'{env_name}' loaded from the latest database entry")
            self.value = self.config_value
        else:
            self.value = env_value

        PERSISTENT_CONFIG_REGISTRY.append(self)

    def __str__(self):
        return str(self.value)

    @property
    def __dict__(self):
        raise TypeError(
            "PersistentConfig object cannot be converted to dict, use config_get or .value instead."
        )

    def __getattribute__(self, item):
        if item == "__dict__":
            raise TypeError(
                "PersistentConfig object cannot be converted to dict, use config_get or .value instead."
            )
        return super().__getattribute__(item)

    def update(self):
        new_value = get_config_value(self.config_path)
        if new_value is not None:
            self.value = new_value
            log.info(f"Updated {self.env_name} to new value {self.value}")

    def save(self):
        log.info(f"Saving '{self.env_name}' to the database")
        path_parts = self.config_path.split(".")
        sub_config = CONFIG_DATA
        for key in path_parts[:-1]:
            if key not in sub_config:
                sub_config[key] = {}
            sub_config = sub_config[key]
        sub_config[path_parts[-1]] = self.value
        save_to_db(CONFIG_DATA)
        self.config_value = self.value


class AppConfig:
    _state: dict[str, PersistentConfig]
    _redis: Optional[redis.Redis] = None

    def __init__(
        self, redis_url: Optional[str] = None, redis_sentinels: Optional[list] = []
    ):
        super().__setattr__("_state", {})
        if redis_url:
            super().__setattr__(
                "_redis",
                get_redis_connection(redis_url, redis_sentinels, decode_responses=True),
            )

    def __setattr__(self, key, value):
        if isinstance(value, PersistentConfig):
            self._state[key] = value
        else:
            self._state[key].value = value
            self._state[key].save()

            if self._redis:
                redis_key = f"the-finance-genie:config:{key}"
                self._redis.set(redis_key, json.dumps(self._state[key].value))

    def __getattr__(self, key):
        if key not in self._state:
            raise AttributeError(f"Config key '{key}' not found")

        # If Redis is available, check for an updated value
        if self._redis:
            redis_key = f"the-finance-genie:config:{key}"
            redis_value = self._redis.get(redis_key)

            if redis_value is not None:
                try:
                    decoded_value = json.loads(redis_value)

                    # Update the in-memory value if different
                    if self._state[key].value != decoded_value:
                        self._state[key].value = decoded_value
                        log.info(f"Updated {key} from Redis: {decoded_value}")

                except json.JSONDecodeError:
                    log.error(f"Invalid JSON format in Redis for {key}: {redis_value}")

        return self._state[key].value


####################################
# WEBUI_AUTH (Required for security)
####################################

ENABLE_API_KEY = PersistentConfig(
    "ENABLE_API_KEY",
    "auth.api_key.enable",
    os.environ.get("ENABLE_API_KEY", "True").lower() == "true",
)

ENABLE_API_KEY_ENDPOINT_RESTRICTIONS = PersistentConfig(
    "ENABLE_API_KEY_ENDPOINT_RESTRICTIONS",
    "auth.api_key.endpoint_restrictions",
    os.environ.get("ENABLE_API_KEY_ENDPOINT_RESTRICTIONS", "False").lower() == "true",
)

API_KEY_ALLOWED_ENDPOINTS = PersistentConfig(
    "API_KEY_ALLOWED_ENDPOINTS",
    "auth.api_key.allowed_endpoints",
    os.environ.get("API_KEY_ALLOWED_ENDPOINTS", ""),
)


JWT_EXPIRES_IN = PersistentConfig(
    "JWT_EXPIRES_IN", "auth.jwt_expiry", os.environ.get("JWT_EXPIRES_IN", "-1")
)

####################################
# OAuth config
####################################

ENABLE_OAUTH_SIGNUP = PersistentConfig(
    "ENABLE_OAUTH_SIGNUP",
    "oauth.enable_signup",
    "True",
)

OAUTH_MERGE_ACCOUNTS_BY_EMAIL = PersistentConfig(
    "OAUTH_MERGE_ACCOUNTS_BY_EMAIL",
    "oauth.merge_accounts_by_email",
    "True",
)

OAUTH_PROVIDERS = {}

OAUTH_CLIENT_ID = PersistentConfig(
    "OAUTH_CLIENT_ID",
    "oauth.oidc.client_id",
    "0oacnb0rzzSF6CfD55d7",
)

OAUTH_CLIENT_SECRET = PersistentConfig(
    "OAUTH_CLIENT_SECRET",
    "oauth.oidc.client_secret",
    "VZmIFmr14fNL_cKWvG5DqUM6DAY1-3rfhAG-zCCopQ5rZL5ssjzOU5Wx0gbvh5Ys",
)

OPENID_PROVIDER_URL = PersistentConfig(
    "OPENID_PROVIDER_URL",
    "oauth.oidc.provider_url",
    "https://dev-80031539-admin.okta.com/oauth2/default/.well-known/openid-configuration",
)

OPENID_REDIRECT_URI = PersistentConfig(
    "OPENID_REDIRECT_URI",
    "oauth.oidc.redirect_uri",
    "http://localhost:8080/oauth/oidc/callback",
)

OAUTH_SCOPES = PersistentConfig(
    "OAUTH_SCOPES",
    "oauth.oidc.scopes",
    "openid email profile groups",
)

OAUTH_PROVIDER_NAME = PersistentConfig(
    "OAUTH_PROVIDER_NAME",
    "oauth.oidc.provider_name",
    "okta",
)

OAUTH_USERNAME_CLAIM = PersistentConfig(
    "OAUTH_USERNAME_CLAIM",
    "oauth.oidc.username_claim",
    "name",
)

OAUTH_PICTURE_CLAIM = PersistentConfig(
    "OAUTH_PICTURE_CLAIM",
    "oauth.oidc.avatar_claim",
    "picture",
)

OAUTH_EMAIL_CLAIM = PersistentConfig(
    "OAUTH_EMAIL_CLAIM",
    "oauth.oidc.email_claim",
    "email",
)

OAUTH_GROUPS_CLAIM = PersistentConfig(
    "OAUTH_GROUPS_CLAIM",
    "oauth.oidc.group_claim",
    "groups",
)

ENABLE_OAUTH_ROLE_MANAGEMENT = PersistentConfig(
    "ENABLE_OAUTH_ROLE_MANAGEMENT",
    "oauth.enable_role_mapping",
    "True",
)

ENABLE_OAUTH_GROUP_MANAGEMENT = PersistentConfig(
    "ENABLE_OAUTH_GROUP_MANAGEMENT",
    "oauth.enable_group_mapping",
    "True",
)

OAUTH_ROLES_CLAIM = PersistentConfig(
    "OAUTH_ROLES_CLAIM",
    "oauth.roles_claim",
    os.environ.get("OAUTH_ROLES_CLAIM", "roles"),
)

OAUTH_ALLOWED_ROLES = PersistentConfig(
    "OAUTH_ALLOWED_ROLES",
    "oauth.allowed_roles",
    ["user", "admin"],
)

OAUTH_ADMIN_ROLES = PersistentConfig(
    "OAUTH_ADMIN_ROLES",
    "oauth.admin_roles",
    ["admin"],
)

OAUTH_ALLOWED_DOMAINS = PersistentConfig(
    "OAUTH_ALLOWED_DOMAINS",
    "oauth.allowed_domains",
    ["*"],
)


def load_oauth_providers():
    OAUTH_PROVIDERS.clear()

    if (
        OAUTH_CLIENT_ID.value
        and OAUTH_CLIENT_SECRET.value
        and OPENID_PROVIDER_URL.value
    ):

        def oidc_oauth_register(client):
            client.register(
                name="oidc",
                client_id=OAUTH_CLIENT_ID.value,
                client_secret=OAUTH_CLIENT_SECRET.value,
                server_metadata_url=OPENID_PROVIDER_URL.value,
                client_kwargs={
                    "scope": OAUTH_SCOPES.value,
                },
                redirect_uri=OPENID_REDIRECT_URI.value,
            )

        OAUTH_PROVIDERS["oidc"] = {
            "name": OAUTH_PROVIDER_NAME.value,
            "redirect_uri": OPENID_REDIRECT_URI.value,
            "register": oidc_oauth_register,
        }


load_oauth_providers()

####################################
# Static DIR
####################################

STATIC_DIR = Path(os.getenv("STATIC_DIR", OPEN_WEBUI_DIR / "static")).resolve()

for file_path in (FRONTEND_BUILD_DIR / "static").glob("**/*"):
    if file_path.is_file():
        target_path = STATIC_DIR / file_path.relative_to(
            (FRONTEND_BUILD_DIR / "static")
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(file_path, target_path)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

frontend_favicon = FRONTEND_BUILD_DIR / "static" / "favicon.png"

if frontend_favicon.exists():
    try:
        shutil.copyfile(frontend_favicon, STATIC_DIR / "favicon.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_splash = FRONTEND_BUILD_DIR / "static" / "splash.png"

if frontend_splash.exists():
    try:
        shutil.copyfile(frontend_splash, STATIC_DIR / "splash.png")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

frontend_loader = FRONTEND_BUILD_DIR / "static" / "loader.js"

if frontend_loader.exists():
    try:
        shutil.copyfile(frontend_loader, STATIC_DIR / "loader.js")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

####################################
# STORAGE PROVIDER
####################################

STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local")  # defaults to local, s3

S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", None)
S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", None)
S3_REGION_NAME = os.environ.get("S3_REGION_NAME", None)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", None)
S3_KEY_PREFIX = os.environ.get("S3_KEY_PREFIX", None)
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", None)
S3_USE_ACCELERATE_ENDPOINT = (
    os.environ.get("S3_USE_ACCELERATE_ENDPOINT", "False").lower() == "true"
)
S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", None)


####################################
# File Upload DIR
####################################

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


####################################
# Cache DIR
####################################

CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


####################################
# DIRECT CONNECTIONS
####################################

ENABLE_DIRECT_CONNECTIONS = PersistentConfig(
    "ENABLE_DIRECT_CONNECTIONS",
    "direct.enable",
    os.environ.get("ENABLE_DIRECT_CONNECTIONS", "True").lower() == "true",
)

####################################
# OLLAMA_BASE_URL
####################################

ENABLE_OLLAMA_API = PersistentConfig(
    "ENABLE_OLLAMA_API",
    "ollama.enable",
    os.environ.get("ENABLE_OLLAMA_API", "True").lower() == "true",
)

OLLAMA_API_BASE_URL = os.environ.get(
    "OLLAMA_API_BASE_URL", "http://localhost:11434/api"
)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "")
if OLLAMA_BASE_URL:
    # Remove trailing slash
    OLLAMA_BASE_URL = (
        OLLAMA_BASE_URL[:-1] if OLLAMA_BASE_URL.endswith("/") else OLLAMA_BASE_URL
    )


K8S_FLAG = os.environ.get("K8S_FLAG", "")
USE_OLLAMA_DOCKER = os.environ.get("USE_OLLAMA_DOCKER", "false")

if OLLAMA_BASE_URL == "" and OLLAMA_API_BASE_URL != "":
    OLLAMA_BASE_URL = (
        OLLAMA_API_BASE_URL[:-4]
        if OLLAMA_API_BASE_URL.endswith("/api")
        else OLLAMA_API_BASE_URL
    )

if ENV == "prod":
    if OLLAMA_BASE_URL == "/ollama" and not K8S_FLAG:
        if USE_OLLAMA_DOCKER.lower() == "true":
            # if you use all-in-one docker container (The Finance Genie + Ollama)
            # with the docker build arg USE_OLLAMA=true (--build-arg="USE_OLLAMA=true") this only works with http://localhost:11434
            OLLAMA_BASE_URL = "http://localhost:11434"
        else:
            OLLAMA_BASE_URL = "http://host.docker.internal:11434"
    elif K8S_FLAG:
        OLLAMA_BASE_URL = "http://ollama-service.the-finance-genie.svc.cluster.local:11434"


OLLAMA_BASE_URLS = os.environ.get("OLLAMA_BASE_URLS", "")
OLLAMA_BASE_URLS = OLLAMA_BASE_URLS if OLLAMA_BASE_URLS != "" else OLLAMA_BASE_URL

OLLAMA_BASE_URLS = [url.strip() for url in OLLAMA_BASE_URLS.split(";")]
OLLAMA_BASE_URLS = PersistentConfig(
    "OLLAMA_BASE_URLS", "ollama.base_urls", OLLAMA_BASE_URLS
)

OLLAMA_API_CONFIGS = PersistentConfig(
    "OLLAMA_API_CONFIGS",
    "ollama.api_configs",
    {},
)

####################################
# OPENAI_API
####################################


ENABLE_OPENAI_API = PersistentConfig(
    "ENABLE_OPENAI_API",
    "openai.enable",
    os.environ.get("ENABLE_OPENAI_API", "True").lower() == "true",
)


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE_URL = os.environ.get("OPENAI_API_BASE_URL", "")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_BASE_URL = os.environ.get("GEMINI_API_BASE_URL", "")


if OPENAI_API_BASE_URL == "":
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"

OPENAI_API_KEYS = os.environ.get("OPENAI_API_KEYS", "")
OPENAI_API_KEYS = OPENAI_API_KEYS if OPENAI_API_KEYS != "" else OPENAI_API_KEY

OPENAI_API_KEYS = [url.strip() for url in OPENAI_API_KEYS.split(";")]
OPENAI_API_KEYS = PersistentConfig(
    "OPENAI_API_KEYS", "openai.api_keys", OPENAI_API_KEYS
)

OPENAI_API_BASE_URLS = os.environ.get("OPENAI_API_BASE_URLS", "")
OPENAI_API_BASE_URLS = (
    OPENAI_API_BASE_URLS if OPENAI_API_BASE_URLS != "" else OPENAI_API_BASE_URL
)

OPENAI_API_BASE_URLS = [
    url.strip() if url != "" else "https://api.openai.com/v1"
    for url in OPENAI_API_BASE_URLS.split(";")
]
OPENAI_API_BASE_URLS = PersistentConfig(
    "OPENAI_API_BASE_URLS", "openai.api_base_urls", OPENAI_API_BASE_URLS
)

OPENAI_API_CONFIGS = PersistentConfig(
    "OPENAI_API_CONFIGS",
    "openai.api_configs",
    {},
)

# Get the actual OpenAI API key based on the base URL
OPENAI_API_KEY = ""
try:
    OPENAI_API_KEY = OPENAI_API_KEYS.value[
        OPENAI_API_BASE_URLS.value.index("https://api.openai.com/v1")
    ]
except Exception:
    pass
OPENAI_API_BASE_URL = "https://api.openai.com/v1"

####################################
# WEBUI
####################################


WEBUI_URL = PersistentConfig(
    "WEBUI_URL", "webui.url", os.environ.get("WEBUI_URL", "http://localhost:3000")
)


ENABLE_SIGNUP = PersistentConfig(
    "ENABLE_SIGNUP",
    "ui.enable_signup",
    (
        False
        if not WEBUI_AUTH
        else os.environ.get("ENABLE_SIGNUP", "True").lower() == "true"
    ),
)

ENABLE_LOGIN_FORM = PersistentConfig(
    "ENABLE_LOGIN_FORM",
    "ui.ENABLE_LOGIN_FORM",
    os.environ.get("ENABLE_LOGIN_FORM", "True").lower() == "true",
)


DEFAULT_LOCALE = PersistentConfig(
    "DEFAULT_LOCALE",
    "ui.default_locale",
    os.environ.get("DEFAULT_LOCALE", ""),
)

DEFAULT_MODELS = PersistentConfig(
    "DEFAULT_MODELS", "ui.default_models", os.environ.get("DEFAULT_MODELS", None)
)

DEFAULT_PROMPT_SUGGESTIONS = PersistentConfig(
    "DEFAULT_PROMPT_SUGGESTIONS",
    "ui.prompt_suggestions",
    [
        {
            "title": ["Help me study", "vocabulary for a college entrance exam"],
            "content": "Help me study vocabulary: write a sentence for me to fill in the blank, and I'll try to pick the correct option.",
        },
        {
            "title": ["Give me ideas", "for what to do with my kids' art"],
            "content": "What are 5 creative things I could do with my kids' art? I don't want to throw them away, but it's also so much clutter.",
        },
        {
            "title": ["Tell me a fun fact", "about the Roman Empire"],
            "content": "Tell me a random fun fact about the Roman Empire",
        },
        {
            "title": ["Show me a code snippet", "of a website's sticky header"],
            "content": "Show me a code snippet of a website's sticky header in CSS and JavaScript.",
        },
        {
            "title": [
                "Explain options trading",
                "if I'm familiar with buying and selling stocks",
            ],
            "content": "Explain options trading in simple terms if I'm familiar with buying and selling stocks.",
        },
        {
            "title": ["Overcome procrastination", "give me tips"],
            "content": "Could you start by asking me about instances when I procrastinate the most and then give me some suggestions to overcome it?",
        },
    ],
)

MODEL_ORDER_LIST = PersistentConfig(
    "MODEL_ORDER_LIST",
    "ui.model_order_list",
    [],
)

DEFAULT_USER_ROLE = PersistentConfig(
    "DEFAULT_USER_ROLE",
    "ui.default_user_role",
    "admin",
)

USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS", "False").lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS = (
    os.environ.get("USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS", "False").lower() == "true"
)

USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)

USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING = (
    os.environ.get(
        "USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING", "False"
    ).lower()
    == "true"
)


USER_PERMISSIONS_CHAT_CONTROLS = (
    os.environ.get("USER_PERMISSIONS_CHAT_CONTROLS", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_FILE_UPLOAD = (
    os.environ.get("USER_PERMISSIONS_CHAT_FILE_UPLOAD", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_DELETE = (
    os.environ.get("USER_PERMISSIONS_CHAT_DELETE", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_EDIT = (
    os.environ.get("USER_PERMISSIONS_CHAT_EDIT", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY", "True").lower() == "true"
)

USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED = (
    os.environ.get("USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED", "False").lower()
    == "true"
)

USER_PERMISSIONS_FEATURES_WEB_SEARCH = (
    os.environ.get("USER_PERMISSIONS_FEATURES_WEB_SEARCH", "True").lower() == "true"
)

USER_PERMISSIONS_FEATURES = {
    "web_search": USER_PERMISSIONS_FEATURES_WEB_SEARCH,
}




DEFAULT_USER_PERMISSIONS = {
    "workspace": {
        "models": USER_PERMISSIONS_WORKSPACE_MODELS_ACCESS,
        "knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ACCESS,
        "prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ACCESS,
        "tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ACCESS,
    },
    "sharing": {
        "public_models": USER_PERMISSIONS_WORKSPACE_MODELS_ALLOW_PUBLIC_SHARING,
        "public_knowledge": USER_PERMISSIONS_WORKSPACE_KNOWLEDGE_ALLOW_PUBLIC_SHARING,
        "public_prompts": USER_PERMISSIONS_WORKSPACE_PROMPTS_ALLOW_PUBLIC_SHARING,
        "public_tools": USER_PERMISSIONS_WORKSPACE_TOOLS_ALLOW_PUBLIC_SHARING,
    },
    "chat": {
        "controls": USER_PERMISSIONS_CHAT_CONTROLS,
        "file_upload": USER_PERMISSIONS_CHAT_FILE_UPLOAD,
        "delete": USER_PERMISSIONS_CHAT_DELETE,
        "edit": USER_PERMISSIONS_CHAT_EDIT,
        "temporary": USER_PERMISSIONS_CHAT_TEMPORARY,
        "temporary_enforced": USER_PERMISSIONS_CHAT_TEMPORARY_ENFORCED,
    },
    "features": {
        "web_search": USER_PERMISSIONS_FEATURES_WEB_SEARCH,
    },
}

USER_PERMISSIONS = PersistentConfig(
    "USER_PERMISSIONS",
    "user.permissions",
    DEFAULT_USER_PERMISSIONS,
)

ENABLE_CHANNELS = PersistentConfig(
    "ENABLE_CHANNELS",
    "channels.enable",
    os.environ.get("ENABLE_CHANNELS", "False").lower() == "true",
)


ENABLE_ADMIN_EXPORT = os.environ.get("ENABLE_ADMIN_EXPORT", "True").lower() == "true"

ENABLE_ADMIN_CHAT_ACCESS = os.environ.get("ENABLE_ADMIN_CHAT_ACCESS", "False").lower() == "true"



def validate_cors_origins(origins):
    for origin in origins:
        if origin != "*":
            validate_cors_origin(origin)


def validate_cors_origin(origin):
    parsed_url = urlparse(origin)

    # Check if the scheme is either http or https
    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(
            f"Invalid scheme in CORS_ALLOW_ORIGIN: '{origin}'. Only 'http' and 'https' are allowed."
        )

    # Ensure that the netloc (domain + port) is present, indicating it's a valid URL
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL structure in CORS_ALLOW_ORIGIN: '{origin}'.")


# For production, you should only need one host as
# fastapi serves the svelte-kit built frontend and backend from the same host and port.
# To test CORS_ALLOW_ORIGIN locally, you can set something like
# CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:8080
# in your .env file depending on your frontend port, 5173 in this case.
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*").split(";")

if "*" in CORS_ALLOW_ORIGIN:
    log.warning(
        "\n\nWARNING: CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION DEPLOYMENTS.\n"
    )

validate_cors_origins(CORS_ALLOW_ORIGIN)




SHOW_ADMIN_DETAILS = PersistentConfig(
    "SHOW_ADMIN_DETAILS",
    "auth.admin.show",
    os.environ.get("SHOW_ADMIN_DETAILS", "true").lower() == "true",
)

ADMIN_EMAIL = PersistentConfig(
    "ADMIN_EMAIL",
    "auth.admin.email",
    os.environ.get("ADMIN_EMAIL", None),
)


####################################
# TASKS
####################################


TASK_MODEL = PersistentConfig(
    "TASK_MODEL",
    "task.model.default",
    os.environ.get("TASK_MODEL", ""),
)

TASK_MODEL_EXTERNAL = PersistentConfig(
    "TASK_MODEL_EXTERNAL",
    "task.model.external",
    os.environ.get("TASK_MODEL_EXTERNAL", ""),
)

TITLE_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "TITLE_GENERATION_PROMPT_TEMPLATE",
    "task.title.prompt_template",
    os.environ.get("TITLE_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate a concise, 3-5 word title summarizing the chat history.
### Guidelines:
- The title should clearly represent the main theme or subject of the conversation.
- Write the title in the chat's primary language; default to English if multilingual.
- Prioritize accuracy over excessive creativity; keep it clear and simple.
### Output:
JSON format: { "title": "your concise title here" }
### Examples:
- { "title": "Stock Market Trends" },
- { "title": "Perfect Chocolate Chip Recipe" },
- { "title": "Evolution of Music Streaming" },
- { "title": "Remote Work Productivity Tips" },
- { "title": "Artificial Intelligence in Healthcare" },
- { "title": "Video Game Development Insights" }
### Chat History:
<chat_history>
{{MESSAGES:END:2}}
</chat_history>"""

TAGS_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "TAGS_GENERATION_PROMPT_TEMPLATE",
    "task.tags.prompt_template",
    os.environ.get("TAGS_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_TAGS_GENERATION_PROMPT_TEMPLATE = """### Task:
Generate 1-3 broad tags categorizing the main themes of the chat history, along with 1-3 more specific subtopic tags.

### Guidelines:
- Start with high-level domains (e.g. Science, Technology, Philosophy, Arts, Politics, Business, Health, Sports, Entertainment, Education)
- Consider including relevant subfields/subdomains if they are strongly represented throughout the conversation
- If content is too short (less than 3 messages) or too diverse, use only ["General"]
- Use the chat's primary language; default to English if multilingual
- Prioritize accuracy over specificity

### Output:
JSON format: { "tags": ["tag1", "tag2", "tag3"] }

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>"""



ENABLE_TAGS_GENERATION = PersistentConfig(
    "ENABLE_TAGS_GENERATION",
    "task.tags.enable",
    os.environ.get("ENABLE_TAGS_GENERATION", "True").lower() == "true",
)

ENABLE_TITLE_GENERATION = PersistentConfig(
    "ENABLE_TITLE_GENERATION",
    "task.title.enable",
    os.environ.get("ENABLE_TITLE_GENERATION", "True").lower() == "true",
)


ENABLE_SEARCH_QUERY_GENERATION = PersistentConfig(
    "ENABLE_SEARCH_QUERY_GENERATION",
    "task.query.search.enable",
    os.environ.get("ENABLE_SEARCH_QUERY_GENERATION", "True").lower() == "true",
)

ENABLE_RETRIEVAL_QUERY_GENERATION = PersistentConfig(
    "ENABLE_RETRIEVAL_QUERY_GENERATION",
    "task.query.retrieval.enable",
    os.environ.get("ENABLE_RETRIEVAL_QUERY_GENERATION", "True").lower() == "true",
)


QUERY_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "QUERY_GENERATION_PROMPT_TEMPLATE",
    "task.query.prompt_template",
    os.environ.get("QUERY_GENERATION_PROMPT_TEMPLATE", ""),
)

DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE = """### Task:
Analyze the chat history to determine the necessity of generating search queries, in the given language. By default, **prioritize generating 1-3 broad and relevant search queries** unless it is absolutely certain that no additional information is required. The aim is to retrieve comprehensive, updated, and valuable information even with minimal uncertainty. If no search is unequivocally needed, return an empty list.

### Guidelines:
- Respond **EXCLUSIVELY** with a JSON object. Any form of extra commentary, explanation, or additional text is strictly prohibited.
- When generating search queries, respond in the format: { "queries": ["query1", "query2"] }, ensuring each query is distinct, concise, and relevant to the topic.
- If and only if it is entirely certain that no useful results can be retrieved by a search, return: { "queries": [] }.
- Err on the side of suggesting search queries if there is **any chance** they might provide useful or updated information.
- Be concise and focused on composing high-quality search queries, avoiding unnecessary elaboration, commentary, or assumptions.
- Today's date is: {{CURRENT_DATE}}.
- Always prioritize providing actionable and broad queries that maximize informational coverage.

### Output:
Strictly return in JSON format: 
{
  "queries": ["query1", "query2"]
}

### Chat History:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
"""

ENABLE_AUTOCOMPLETE_GENERATION = PersistentConfig(
    "ENABLE_AUTOCOMPLETE_GENERATION",
    "task.autocomplete.enable",
    os.environ.get("ENABLE_AUTOCOMPLETE_GENERATION", "False").lower() == "true",
)

AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = PersistentConfig(
    "AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH",
    "task.autocomplete.input_max_length",
    int(os.environ.get("AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH", "-1")),
)

AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = PersistentConfig(
    "AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE",
    "task.autocomplete.prompt_template",
    os.environ.get("AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE", ""),
)


DEFAULT_AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = """### Task:
You are an autocompletion system. Continue the text in `<text>` based on the **completion type** in `<type>` and the given language.  

### **Instructions**:
1. Analyze `<text>` for context and meaning.  
2. Use `<type>` to guide your output:  
   - **General**: Provide a natural, concise continuation.  
   - **Search Query**: Complete as if generating a realistic search query.  
3. Start as if you are directly continuing `<text>`. Do **not** repeat, paraphrase, or respond as a model. Simply complete the text.  
4. Ensure the continuation:
   - Flows naturally from `<text>`.  
   - Avoids repetition, overexplaining, or unrelated ideas.  
5. If unsure, return: `{ "text": "" }`.  

### **Output Rules**:
- Respond only in JSON format: `{ "text": "<your_completion>" }`.

### **Examples**:
#### Example 1:  
Input:  
<type>General</type>  
<text>The sun was setting over the horizon, painting the sky</text>  
Output:  
{ "text": "with vibrant shades of orange and pink." }

#### Example 2:  
Input:  
<type>Search Query</type>  
<text>Top-rated restaurants in</text>  
Output:  
{ "text": "New York City for Italian cuisine." }  

---
### Context:
<chat_history>
{{MESSAGES:END:6}}
</chat_history>
<type>{{TYPE}}</type>  
<text>{{PROMPT}}</text>  
#### Output:
"""

TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = PersistentConfig(
    "TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE",
    "task.tools.prompt_template",
    os.environ.get("TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE", ""),
)


DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = """Available Tools: {{TOOLS}}

Your task is to choose and return the correct tool(s) from the list of available tools based on the query. Follow these guidelines:

- Return only the JSON object, without any additional text or explanation.

- If no tools match the query, return an empty array: 
   {
     "tool_calls": []
   }

- If one or more tools match the query, construct a JSON response containing a "tool_calls" array with objects that include:
   - "name": The tool's name.
   - "parameters": A dictionary of required parameters and their corresponding values.

The format for the JSON response is strictly:
{
  "tool_calls": [
    {"name": "toolName1", "parameters": {"key1": "value1"}},
    {"name": "toolName2", "parameters": {"key2": "value2"}}
  ]
}"""



DEFAULT_MOA_GENERATION_PROMPT_TEMPLATE = """You have been provided with a set of responses from various models to the latest user query: "{{prompt}}"

Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models: {{responses}}"""

####################################
# Vector Database
####################################

VECTOR_DB = os.environ.get("VECTOR_DB", "chroma")

# Chroma
CHROMA_DATA_PATH = f"{DATA_DIR}/vector_db"

if VECTOR_DB == "chroma":
    import chromadb

    CHROMA_TENANT = os.environ.get("CHROMA_TENANT", chromadb.DEFAULT_TENANT)
    CHROMA_DATABASE = os.environ.get("CHROMA_DATABASE", chromadb.DEFAULT_DATABASE)
    CHROMA_HTTP_HOST = os.environ.get("CHROMA_HTTP_HOST", "")
    CHROMA_HTTP_PORT = int(os.environ.get("CHROMA_HTTP_PORT", "8000"))
    CHROMA_CLIENT_AUTH_PROVIDER = os.environ.get("CHROMA_CLIENT_AUTH_PROVIDER", "")
    CHROMA_CLIENT_AUTH_CREDENTIALS = os.environ.get(
        "CHROMA_CLIENT_AUTH_CREDENTIALS", ""
    )
    # Comma-separated list of header=value pairs
    CHROMA_HTTP_HEADERS = os.environ.get("CHROMA_HTTP_HEADERS", "")
    if CHROMA_HTTP_HEADERS:
        CHROMA_HTTP_HEADERS = dict(
            [pair.split("=") for pair in CHROMA_HTTP_HEADERS.split(",")]
        )
    else:
        CHROMA_HTTP_HEADERS = None
    CHROMA_HTTP_SSL = os.environ.get("CHROMA_HTTP_SSL", "false").lower() == "true"
# this uses the model defined in the Dockerfile ENV variable. If you dont use docker or docker based deployments such as k8s, the default embedding model will be used (sentence-transformers/all-MiniLM-L6-v2)

# Milvus

MILVUS_URI = os.environ.get("MILVUS_URI", f"{DATA_DIR}/vector_db/milvus.db")
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", None)

# Qdrant
QDRANT_URI = os.environ.get("QDRANT_URI", None)
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", None)

# OpenSearch
OPENSEARCH_URI = os.environ.get("OPENSEARCH_URI", "https://localhost:9200")
OPENSEARCH_SSL = os.environ.get("OPENSEARCH_SSL", "true").lower() == "true"
OPENSEARCH_CERT_VERIFY = (
    os.environ.get("OPENSEARCH_CERT_VERIFY", "false").lower() == "true"
)
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME", None)
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD", None)

# ElasticSearch
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "https://localhost:9200")
ELASTICSEARCH_CA_CERTS = os.environ.get("ELASTICSEARCH_CA_CERTS", None)
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY", None)
ELASTICSEARCH_USERNAME = os.environ.get("ELASTICSEARCH_USERNAME", None)
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD", None)
ELASTICSEARCH_CLOUD_ID = os.environ.get("ELASTICSEARCH_CLOUD_ID", None)
SSL_ASSERT_FINGERPRINT = os.environ.get("SSL_ASSERT_FINGERPRINT", None)
ELASTICSEARCH_INDEX_PREFIX = os.environ.get(
    "ELASTICSEARCH_INDEX_PREFIX", "open_webui_collections"
)
# Pgvector
PGVECTOR_DB_URL = os.environ.get("PGVECTOR_DB_URL", DATABASE_URL)
if VECTOR_DB == "pgvector" and not PGVECTOR_DB_URL.startswith("postgres"):
    raise ValueError(
        "Pgvector requires setting PGVECTOR_DB_URL or using Postgres with vector extension as the primary database."
    )
PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH = int(
    os.environ.get("PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH", "1536")
)

####################################
# Information Retrieval (RAG)
####################################


# If configured, Google Drive will be available as an upload option.
ENABLE_GOOGLE_DRIVE_INTEGRATION = PersistentConfig(
    "ENABLE_GOOGLE_DRIVE_INTEGRATION",
    "google_drive.enable",
    os.getenv("ENABLE_GOOGLE_DRIVE_INTEGRATION", "False").lower() == "true",
)

GOOGLE_DRIVE_CLIENT_ID = PersistentConfig(
    "GOOGLE_DRIVE_CLIENT_ID",
    "google_drive.client_id",
    os.environ.get("GOOGLE_DRIVE_CLIENT_ID", ""),
)

GOOGLE_DRIVE_API_KEY = PersistentConfig(
    "GOOGLE_DRIVE_API_KEY",
    "google_drive.api_key",
    os.environ.get("GOOGLE_DRIVE_API_KEY", ""),
)

ENABLE_ONEDRIVE_INTEGRATION = PersistentConfig(
    "ENABLE_ONEDRIVE_INTEGRATION",
    "onedrive.enable",
    os.getenv("ENABLE_ONEDRIVE_INTEGRATION", "False").lower() == "true",
)

ONEDRIVE_CLIENT_ID = PersistentConfig(
    "ONEDRIVE_CLIENT_ID",
    "onedrive.client_id",
    os.environ.get("ONEDRIVE_CLIENT_ID", ""),
)

# RAG Content Extraction
CONTENT_EXTRACTION_ENGINE = PersistentConfig(
    "CONTENT_EXTRACTION_ENGINE",
    "rag.CONTENT_EXTRACTION_ENGINE",
    os.environ.get("CONTENT_EXTRACTION_ENGINE", "").lower(),
)

TIKA_SERVER_URL = PersistentConfig(
    "TIKA_SERVER_URL",
    "rag.tika_server_url",
    os.getenv("TIKA_SERVER_URL", "http://tika:9998"),  # Default for sidecar deployment
)

DOCLING_SERVER_URL = PersistentConfig(
    "DOCLING_SERVER_URL",
    "rag.docling_server_url",
    os.getenv("DOCLING_SERVER_URL", "http://docling:5001"),
)

DOCUMENT_INTELLIGENCE_ENDPOINT = PersistentConfig(
    "DOCUMENT_INTELLIGENCE_ENDPOINT",
    "rag.document_intelligence_endpoint",
    os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
)

DOCUMENT_INTELLIGENCE_KEY = PersistentConfig(
    "DOCUMENT_INTELLIGENCE_KEY",
    "rag.document_intelligence_key",
    os.getenv("DOCUMENT_INTELLIGENCE_KEY", ""),
)


BYPASS_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_EMBEDDING_AND_RETRIEVAL",
    "rag.bypass_embedding_and_retrieval",
    os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)


RAG_TOP_K = PersistentConfig(
    "RAG_TOP_K", "rag.top_k", int(os.environ.get("RAG_TOP_K", "3"))
)
RAG_TOP_K_RERANKER = PersistentConfig(
    "RAG_TOP_K_RERANKER",
    "rag.top_k_reranker",
    int(os.environ.get("RAG_TOP_K_RERANKER", "3")),
)
RAG_RELEVANCE_THRESHOLD = PersistentConfig(
    "RAG_RELEVANCE_THRESHOLD",
    "rag.relevance_threshold",
    float(os.environ.get("RAG_RELEVANCE_THRESHOLD", "0.0")),
)

ENABLE_RAG_HYBRID_SEARCH = PersistentConfig(
    "ENABLE_RAG_HYBRID_SEARCH",
    "rag.enable_hybrid_search",
    os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "").lower() == "true",
)

RAG_FULL_CONTEXT = PersistentConfig(
    "RAG_FULL_CONTEXT",
    "rag.full_context",
    os.getenv("RAG_FULL_CONTEXT", "False").lower() == "true",
)

RAG_FILE_MAX_COUNT = PersistentConfig(
    "RAG_FILE_MAX_COUNT",
    "rag.file.max_count",
    (
        int(os.environ.get("RAG_FILE_MAX_COUNT"))
        if os.environ.get("RAG_FILE_MAX_COUNT")
        else None
    ),
)

RAG_FILE_MAX_SIZE = PersistentConfig(
    "RAG_FILE_MAX_SIZE",
    "rag.file.max_size",
    (
        int(os.environ.get("RAG_FILE_MAX_SIZE"))
        if os.environ.get("RAG_FILE_MAX_SIZE")
        else None
    ),
)

ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = PersistentConfig(
    "ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION",
    "rag.enable_web_loader_ssl_verification",
    os.environ.get("ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION", "True").lower() == "true",
)

RAG_EMBEDDING_ENGINE = PersistentConfig(
    "RAG_EMBEDDING_ENGINE",
    "rag.embedding_engine",
    os.environ.get("RAG_EMBEDDING_ENGINE", ""),
)

PDF_EXTRACT_IMAGES = PersistentConfig(
    "PDF_EXTRACT_IMAGES",
    "rag.pdf_extract_images",
    os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true",
)

RAG_EMBEDDING_MODEL = PersistentConfig(
    "RAG_EMBEDDING_MODEL",
    "rag.embedding_model",
    os.environ.get("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
)
log.info(f"Embedding model set: {RAG_EMBEDDING_MODEL.value}")

RAG_EMBEDDING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("RAG_EMBEDDING_MODEL_AUTO_UPDATE", "True").lower() == "true"
)

RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
)

RAG_EMBEDDING_BATCH_SIZE = PersistentConfig(
    "RAG_EMBEDDING_BATCH_SIZE",
    "rag.embedding_batch_size",
    int(
        os.environ.get("RAG_EMBEDDING_BATCH_SIZE")
        or os.environ.get("RAG_EMBEDDING_OPENAI_BATCH_SIZE", "1")
    ),
)

RAG_EMBEDDING_QUERY_PREFIX = os.environ.get("RAG_EMBEDDING_QUERY_PREFIX", None)

RAG_EMBEDDING_CONTENT_PREFIX = os.environ.get("RAG_EMBEDDING_CONTENT_PREFIX", None)

RAG_EMBEDDING_PREFIX_FIELD_NAME = os.environ.get(
    "RAG_EMBEDDING_PREFIX_FIELD_NAME", None
)

RAG_RERANKING_MODEL = PersistentConfig(
    "RAG_RERANKING_MODEL",
    "rag.reranking_model",
    os.environ.get("RAG_RERANKING_MODEL", ""),
)
if RAG_RERANKING_MODEL.value != "":
    log.info(f"Reranking model set: {RAG_RERANKING_MODEL.value}")

RAG_RERANKING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("RAG_RERANKING_MODEL_AUTO_UPDATE", "True").lower() == "true"
)

RAG_RERANKING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_RERANKING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
)


RAG_TEXT_SPLITTER = PersistentConfig(
    "RAG_TEXT_SPLITTER",
    "rag.text_splitter",
    os.environ.get("RAG_TEXT_SPLITTER", ""),
)


TIKTOKEN_CACHE_DIR = os.environ.get("TIKTOKEN_CACHE_DIR", f"{CACHE_DIR}/tiktoken")
TIKTOKEN_ENCODING_NAME = PersistentConfig(
    "TIKTOKEN_ENCODING_NAME",
    "rag.tiktoken_encoding_name",
    os.environ.get("TIKTOKEN_ENCODING_NAME", "cl100k_base"),
)


CHUNK_SIZE = PersistentConfig(
    "CHUNK_SIZE", "rag.chunk_size", int(os.environ.get("CHUNK_SIZE", "1000"))
)
CHUNK_OVERLAP = PersistentConfig(
    "CHUNK_OVERLAP",
    "rag.chunk_overlap",
    int(os.environ.get("CHUNK_OVERLAP", "100")),
)

DEFAULT_RAG_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [source_id] **only when the <source_id> tag is explicitly provided** in the context.

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [source_id] (e.g., [1], [2]) when a `<source_id>` tag is explicitly provided in the context.**
- Do not cite if the <source_id> tag is not provided in the context.  
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in "whitepaper.pdf" with a provided <source_id>, the response should include the citation like so:  
* "According to the study, the proposed method increases efficiency by 20% [whitepaper.pdf]."
If no <source_id> is present, the response should omit the citation.

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [source_id] only when the <source_id> tag is present in the context.

<context>
{{CONTEXT}}
</context>

<user_query>
{{QUERY}}
</user_query>
"""

RAG_TEMPLATE = PersistentConfig(
    "RAG_TEMPLATE",
    "rag.template",
    os.environ.get("RAG_TEMPLATE", DEFAULT_RAG_TEMPLATE),
)

RAG_OPENAI_API_BASE_URL = PersistentConfig(
    "RAG_OPENAI_API_BASE_URL",
    "rag.openai_api_base_url",
    os.getenv("RAG_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)
RAG_OPENAI_API_KEY = PersistentConfig(
    "RAG_OPENAI_API_KEY",
    "rag.openai_api_key",
    os.getenv("RAG_OPENAI_API_KEY", OPENAI_API_KEY),
)

RAG_OLLAMA_BASE_URL = PersistentConfig(
    "RAG_OLLAMA_BASE_URL",
    "rag.ollama.url",
    os.getenv("RAG_OLLAMA_BASE_URL", OLLAMA_BASE_URL),
)

RAG_OLLAMA_API_KEY = PersistentConfig(
    "RAG_OLLAMA_API_KEY",
    "rag.ollama.key",
    os.getenv("RAG_OLLAMA_API_KEY", ""),
)


ENABLE_RAG_LOCAL_WEB_FETCH = (
    os.getenv("ENABLE_RAG_LOCAL_WEB_FETCH", "False").lower() == "true"
)

YOUTUBE_LOADER_LANGUAGE = PersistentConfig(
    "YOUTUBE_LOADER_LANGUAGE",
    "rag.youtube_loader_language",
    os.getenv("YOUTUBE_LOADER_LANGUAGE", "en").split(","),
)

YOUTUBE_LOADER_PROXY_URL = PersistentConfig(
    "YOUTUBE_LOADER_PROXY_URL",
    "rag.youtube_loader_proxy_url",
    os.getenv("YOUTUBE_LOADER_PROXY_URL", ""),
)


ENABLE_RAG_WEB_SEARCH = PersistentConfig(
    "ENABLE_RAG_WEB_SEARCH",
    "rag.web.search.enable",
    os.getenv("ENABLE_RAG_WEB_SEARCH", "False").lower() == "true",
)

RAG_WEB_SEARCH_ENGINE = PersistentConfig(
    "RAG_WEB_SEARCH_ENGINE",
    "rag.web.search.engine",
    os.getenv("RAG_WEB_SEARCH_ENGINE", ""),
)

BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL",
    "rag.web.search.bypass_embedding_and_retrieval",
    os.getenv("BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)

# You can provide a list of your own websites to filter after performing a web search.
# This ensures the highest level of safety and reliability of the information sources.
RAG_WEB_SEARCH_DOMAIN_FILTER_LIST = PersistentConfig(
    "RAG_WEB_SEARCH_DOMAIN_FILTER_LIST",
    "rag.web.search.domain.filter_list",
    [
        # "wikipedia.com",
        # "wikimedia.org",
        # "wikidata.org",
    ],
)


SEARXNG_QUERY_URL = PersistentConfig(
    "SEARXNG_QUERY_URL",
    "rag.web.search.searxng_query_url",
    os.getenv("SEARXNG_QUERY_URL", ""),
)

GOOGLE_PSE_API_KEY = PersistentConfig(
    "GOOGLE_PSE_API_KEY",
    "rag.web.search.google_pse_api_key",
    os.getenv("GOOGLE_PSE_API_KEY", ""),
)

GOOGLE_PSE_ENGINE_ID = PersistentConfig(
    "GOOGLE_PSE_ENGINE_ID",
    "rag.web.search.google_pse_engine_id",
    os.getenv("GOOGLE_PSE_ENGINE_ID", ""),
)

BRAVE_SEARCH_API_KEY = PersistentConfig(
    "BRAVE_SEARCH_API_KEY",
    "rag.web.search.brave_search_api_key",
    os.getenv("BRAVE_SEARCH_API_KEY", ""),
)

KAGI_SEARCH_API_KEY = PersistentConfig(
    "KAGI_SEARCH_API_KEY",
    "rag.web.search.kagi_search_api_key",
    os.getenv("KAGI_SEARCH_API_KEY", ""),
)

MOJEEK_SEARCH_API_KEY = PersistentConfig(
    "MOJEEK_SEARCH_API_KEY",
    "rag.web.search.mojeek_search_api_key",
    os.getenv("MOJEEK_SEARCH_API_KEY", ""),
)

BOCHA_SEARCH_API_KEY = PersistentConfig(
    "BOCHA_SEARCH_API_KEY",
    "rag.web.search.bocha_search_api_key",
    os.getenv("BOCHA_SEARCH_API_KEY", ""),
)

SERPSTACK_API_KEY = PersistentConfig(
    "SERPSTACK_API_KEY",
    "rag.web.search.serpstack_api_key",
    os.getenv("SERPSTACK_API_KEY", ""),
)

SERPSTACK_HTTPS = PersistentConfig(
    "SERPSTACK_HTTPS",
    "rag.web.search.serpstack_https",
    os.getenv("SERPSTACK_HTTPS", "True").lower() == "true",
)

SERPER_API_KEY = PersistentConfig(
    "SERPER_API_KEY",
    "rag.web.search.serper_api_key",
    os.getenv("SERPER_API_KEY", ""),
)

SERPLY_API_KEY = PersistentConfig(
    "SERPLY_API_KEY",
    "rag.web.search.serply_api_key",
    os.getenv("SERPLY_API_KEY", ""),
)

TAVILY_API_KEY = PersistentConfig(
    "TAVILY_API_KEY",
    "rag.web.search.tavily_api_key",
    os.getenv("TAVILY_API_KEY", ""),
)

TAVILY_EXTRACT_DEPTH = PersistentConfig(
    "TAVILY_EXTRACT_DEPTH",
    "rag.web.search.tavily_extract_depth",
    os.getenv("TAVILY_EXTRACT_DEPTH", "basic"),
)

JINA_API_KEY = PersistentConfig(
    "JINA_API_KEY",
    "rag.web.search.jina_api_key",
    os.getenv("JINA_API_KEY", ""),
)

SEARCHAPI_API_KEY = PersistentConfig(
    "SEARCHAPI_API_KEY",
    "rag.web.search.searchapi_api_key",
    os.getenv("SEARCHAPI_API_KEY", ""),
)

SEARCHAPI_ENGINE = PersistentConfig(
    "SEARCHAPI_ENGINE",
    "rag.web.search.searchapi_engine",
    os.getenv("SEARCHAPI_ENGINE", ""),
)

SERPAPI_API_KEY = PersistentConfig(
    "SERPAPI_API_KEY",
    "rag.web.search.serpapi_api_key",
    os.getenv("SERPAPI_API_KEY", ""),
)

SERPAPI_ENGINE = PersistentConfig(
    "SERPAPI_ENGINE",
    "rag.web.search.serpapi_engine",
    os.getenv("SERPAPI_ENGINE", ""),
)

BING_SEARCH_V7_ENDPOINT = PersistentConfig(
    "BING_SEARCH_V7_ENDPOINT",
    "rag.web.search.bing_search_v7_endpoint",
    os.environ.get(
        "BING_SEARCH_V7_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
    ),
)

BING_SEARCH_V7_SUBSCRIPTION_KEY = PersistentConfig(
    "BING_SEARCH_V7_SUBSCRIPTION_KEY",
    "rag.web.search.bing_search_v7_subscription_key",
    os.environ.get("BING_SEARCH_V7_SUBSCRIPTION_KEY", ""),
)

EXA_API_KEY = PersistentConfig(
    "EXA_API_KEY",
    "rag.web.search.exa_api_key",
    os.getenv("EXA_API_KEY", ""),
)

PERPLEXITY_API_KEY = PersistentConfig(
    "PERPLEXITY_API_KEY",
    "rag.web.search.perplexity_api_key",
    os.getenv("PERPLEXITY_API_KEY", ""),
)

RAG_WEB_SEARCH_RESULT_COUNT = PersistentConfig(
    "RAG_WEB_SEARCH_RESULT_COUNT",
    "rag.web.search.result_count",
    int(os.getenv("RAG_WEB_SEARCH_RESULT_COUNT", "3")),
)

RAG_WEB_SEARCH_CONCURRENT_REQUESTS = PersistentConfig(
    "RAG_WEB_SEARCH_CONCURRENT_REQUESTS",
    "rag.web.search.concurrent_requests",
    int(os.getenv("RAG_WEB_SEARCH_CONCURRENT_REQUESTS", "10")),
)

RAG_WEB_LOADER_ENGINE = PersistentConfig(
    "RAG_WEB_LOADER_ENGINE",
    "rag.web.loader.engine",
    os.environ.get("RAG_WEB_LOADER_ENGINE", "safe_web"),
)

RAG_WEB_SEARCH_TRUST_ENV = PersistentConfig(
    "RAG_WEB_SEARCH_TRUST_ENV",
    "rag.web.search.trust_env",
    os.getenv("RAG_WEB_SEARCH_TRUST_ENV", "False").lower() == "true",
)

PLAYWRIGHT_WS_URI = PersistentConfig(
    "PLAYWRIGHT_WS_URI",
    "rag.web.loader.engine.playwright.ws.uri",
    os.environ.get("PLAYWRIGHT_WS_URI", None),
)

PLAYWRIGHT_TIMEOUT = PersistentConfig(
    "PLAYWRIGHT_TIMEOUT",
    "rag.web.loader.engine.playwright.timeout",
    int(os.environ.get("PLAYWRIGHT_TIMEOUT", "10")),
)

FIRECRAWL_API_KEY = PersistentConfig(
    "FIRECRAWL_API_KEY",
    "firecrawl.api_key",
    os.environ.get("FIRECRAWL_API_KEY", ""),
)

FIRECRAWL_API_BASE_URL = PersistentConfig(
    "FIRECRAWL_API_BASE_URL",
    "firecrawl.api_url",
    os.environ.get("FIRECRAWL_API_BASE_URL", "https://api.firecrawl.dev"),
)