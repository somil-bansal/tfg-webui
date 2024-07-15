from pydantic import BaseModel
from typing import List, Union, Optional
import time
import uuid
import logging
from peewee import *

from apps.webui.models.users import UserModel, Users

from apps.webui.internal.db import DB

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# DB MODEL
####################


class Auth(Model):
    id = CharField(unique=True)
    email = CharField()
    password = TextField()
    active = BooleanField()

    class Meta:
        database = DB


class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    active: bool = True


####################
# Forms
####################


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str


class AuthsTable:
    def __init__(self, db):
        self.db = db
        self.db.create_tables([Auth])

    def insert_new_auth(
            self,
            email: str,
            password: str,
            name: str,
            profile_image_url: str = "/user.png",
            role: str = "user",
            oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        log.info("insert_new_auth")

        # id = str(uuid.uuid4())
        id = oauth_sub

        auth = AuthModel(
            **{"id": id, "email": email, "password": password, "active": True}
        )
        result = Auth.create(**auth.model_dump())

        user = Users.insert_new_user(
            id, name, email, profile_image_url, role, oauth_sub
        )

        if result and user:
            return user
        else:
            return None


Auths = AuthsTable(DB)
