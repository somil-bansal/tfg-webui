"""Peewee migrations -- 001_initial.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""
    
    @migrator.create_model
    class Chat(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        title = pw.TextField()
        chat = pw.TextField()
        created_at = pw.BigIntegerField()
        updated_at = pw.BigIntegerField()
        share_id = pw.CharField(max_length=255, null=True, unique=True)
        archived = pw.BooleanField(default=False)

        class Meta:
            table_name = "chat"

    @migrator.create_model
    class ChatIdTag(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        tag_name = pw.CharField(max_length=255)
        chat_id = pw.CharField(max_length=255)
        user_id = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "chatidtag"

    @migrator.create_model
    class Document(pw.Model):
        id = pw.AutoField()
        collection_name = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255, unique=True)
        title = pw.TextField()
        filename = pw.TextField()
        content = pw.TextField(null=True)
        user_groups = pw.TextField()
        user_id = pw.CharField(max_length=255)
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "document"

    @migrator.create_model
    class File(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        filename = pw.TextField()
        meta = pw.TextField()
        created_at = pw.BigIntegerField()

        class Meta:
            table_name = "file"

    @migrator.create_model
    class Function(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        name = pw.TextField()
        type = pw.TextField()
        content = pw.TextField()
        meta = pw.TextField()
        valves = pw.TextField()
        is_active = pw.BooleanField(default=False)
        is_global = pw.BooleanField(default=False)
        updated_at = pw.BigIntegerField()
        created_at = pw.BigIntegerField()

        class Meta:
            table_name = "function"

    @migrator.create_model
    class Memory(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        content = pw.TextField()
        updated_at = pw.BigIntegerField()
        created_at = pw.BigIntegerField()

        class Meta:
            table_name = "memory"

    @migrator.create_model
    class Model(pw.Model):
        id = pw.TextField(unique=True)
        user_id = pw.TextField()
        base_model_id = pw.TextField(null=True)
        name = pw.TextField()
        params = pw.TextField()
        meta = pw.TextField()
        updated_at = pw.BigIntegerField()
        created_at = pw.BigIntegerField()

        class Meta:
            table_name = "model"

    @migrator.create_model
    class Prompt(pw.Model):
        id = pw.AutoField()
        command = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        title = pw.TextField()
        content = pw.TextField()
        timestamp = pw.BigIntegerField()

        class Meta:
            table_name = "prompt"

    @migrator.create_model
    class Tag(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255)
        user_id = pw.CharField(max_length=255)
        data = pw.TextField(null=True)

        class Meta:
            table_name = "tag"

    @migrator.create_model
    class Tool(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        user_id = pw.CharField(max_length=255)
        name = pw.TextField()
        content = pw.TextField()
        specs = pw.TextField()
        meta = pw.TextField()
        valves = pw.TextField()
        updated_at = pw.BigIntegerField()
        created_at = pw.BigIntegerField()

        class Meta:
            table_name = "tool"

    @migrator.create_model
    class User(pw.Model):
        id = pw.CharField(max_length=255, unique=True)
        name = pw.CharField(max_length=255)
        email = pw.CharField(max_length=255)
        groups = pw.TextField()
        role = pw.CharField(max_length=255)
        profile_image_url = pw.TextField()
        last_active_at = pw.BigIntegerField()
        updated_at = pw.BigIntegerField()
        created_at = pw.BigIntegerField()
        settings = pw.TextField(null=True)

        class Meta:
            table_name = "user"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    migrator.remove_model('user')

    migrator.remove_model('tool')

    migrator.remove_model('tag')

    migrator.remove_model('prompt')

    migrator.remove_model('model')

    migrator.remove_model('memory')

    migrator.remove_model('function')

    migrator.remove_model('file')

    migrator.remove_model('document')

    migrator.remove_model('chatidtag')

    migrator.remove_model('chat')
