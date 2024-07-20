import json
import time
from typing import List, Optional

from peewee import *
from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel, ConfigDict

from apps.webui.internal.db import DB, JSONField


####################
# User DB Schema
####################


class User(Model):
    id = CharField(unique=True)
    name = CharField()
    email = CharField()
    groups = TextField()
    role = CharField()
    profile_image_url = TextField()

    last_active_at = BigIntegerField()
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    settings = JSONField(null=True)

    class Meta:
        database = DB

    def save(self, *args, **kwargs):
        # Convert groups list to JSON string before saving
        if isinstance(self.groups, list):
            self.groups = json.dumps(self.groups)
        super(User, self).save(*args, **kwargs)

    @classmethod
    def from_db(cls, user):
        # Convert groups JSON string back to list after retrieving from DB
        if isinstance(user.groups, str):
            user.groups = json.loads(user.groups)
        return user


class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass


class UserModel(BaseModel):
    id: str
    email: str
    name: str
    groups: List[str]
    role: str
    profile_image_url: Optional[str] = '/favicon.png'

    last_active_at: Optional[int] = None  # timestamp in epoch
    updated_at: Optional[int] = None  # timestamp in epoch
    created_at: Optional[int] = None  # timestamp in epoch

    settings: Optional[UserSettings] = None


####################
# Forms
####################


class UserRoleUpdateForm(BaseModel):
    id: str
    role: str


class UsersTable:
    def __init__(self, db):
        self.db = db
        self.db.create_tables([User])

    def insert_new_user(
            self,
            id: str,
            name: str,
            email: str,
            profile_image_url: str = "/user.png",
            role: str = "user",
            groups: List[str] = ["tfg"],
    ) -> Optional[UserModel]:
        user = UserModel(
            **{
                "id": id,
                "name": name,
                "email": email,
                "groups": groups,
                "role": role,
                "profile_image_url": profile_image_url,
                "last_active_at": int(time.time()),
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        result = User.create(**user.model_dump())
        if result:
            return user
        else:
            return None

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            user = User.get(User.id == id)
            user = User.from_db(user)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            user = User.get(User.email == email)
            user = User.from_db(user)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def get_users(self, skip: int = 0, limit: int = 50) -> List[UserModel]:
        users = User.select().limit(limit).offset(skip)
        return [
            UserModel(**model_to_dict(User.from_db(user)))
            for user in users
        ]

    def get_num_users(self) -> Optional[int]:
        return User.select().count()

    def get_first_user(self) -> UserModel:
        try:
            user = User.select().order_by(User.created_at).first()
            user = User.from_db(user)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        try:
            query = User.update(last_active_at=int(time.time())).where(User.id == id)
            query.execute()

            user = User.get(User.id == id)
            user = User.from_db(user)
            return UserModel(**model_to_dict(user))
        except:
            return None

    def update_groups(self, id: str, groups:[str]):
        try:
            query = User.update(groups=json.dumps(groups)).where(User.id == id)
            query.execute()
            user = User.get(User.id == id)
            user = User.from_db(user)
            return UserModel(**model_to_dict(user))
        except:
            return None


####################
# Forms
####################


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    groups: List[str]
    profile_image_url: str


Users = UsersTable(DB)
