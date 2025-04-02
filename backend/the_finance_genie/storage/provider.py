import os
import shutil
import json
import logging
from abc import ABC, abstractmethod
from typing import BinaryIO, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from the_finance_genie.config import (
    S3_ACCESS_KEY_ID,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
    S3_KEY_PREFIX,
    S3_REGION_NAME,
    S3_SECRET_ACCESS_KEY,
    S3_USE_ACCELERATE_ENDPOINT,
    S3_ADDRESSING_STYLE,
    UPLOAD_DIR,
)
from the_finance_genie.constants import ERROR_MESSAGES
from the_finance_genie.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class StorageProvider(ABC):
    @abstractmethod
    def get_file(self, file_path: str) -> str:
        pass

    @abstractmethod
    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        pass

    @abstractmethod
    def delete_all_files(self) -> None:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        pass


class LocalStorageProvider(StorageProvider):
    @staticmethod
    def upload_file(file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        contents = file.read()
        if not contents:
            raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)
        file_path = f"{UPLOAD_DIR}/{filename}"
        with open(file_path, "wb") as f:
            f.write(contents)
        return contents, file_path

    @staticmethod
    def get_file(file_path: str) -> str:
        """Handles downloading of the file from local storage."""
        return file_path

    @staticmethod
    def delete_file(file_path: str) -> None:
        """Handles deletion of the file from local storage."""
        filename = file_path.split("/")[-1]
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            log.warning(f"File {file_path} not found in local storage.")

    @staticmethod
    def delete_all_files() -> None:
        """Handles deletion of all files from local storage."""
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f"Failed to delete {file_path}. Reason: {e}")
        else:
            log.warning(f"Directory {UPLOAD_DIR} not found in local storage.")


class S3StorageProvider(StorageProvider):
    def __init__(self):
        config = Config(
            s3={
                "use_accelerate_endpoint": S3_USE_ACCELERATE_ENDPOINT,
                "addressing_style": S3_ADDRESSING_STYLE,
            },
        )

        # If access key and secret are provided, use them for authentication
        if S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                aws_access_key_id=S3_ACCESS_KEY_ID,
                aws_secret_access_key=S3_SECRET_ACCESS_KEY,
                config=config,
            )
        else:
            # If no explicit credentials are provided, fall back to default AWS credentials
            # This supports workload identity (IAM roles for EC2, EKS, etc.)
            self.s3_client = boto3.client(
                "s3",
                region_name=S3_REGION_NAME,
                endpoint_url=S3_ENDPOINT_URL,
                config=config,
            )

        self.bucket_name = S3_BUCKET_NAME
        self.key_prefix = S3_KEY_PREFIX if S3_KEY_PREFIX else ""

    def upload_file(self, file: BinaryIO, filename: str) -> Tuple[bytes, str]:
        """Handles uploading of the file to S3 storage."""
        _, file_path = LocalStorageProvider.upload_file(file, filename)
        try:
            s3_key = os.path.join(self.key_prefix, filename)
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            return (
                open(file_path, "rb").read(),
                "s3://" + self.bucket_name + "/" + s3_key,
            )
        except ClientError as e:
            raise RuntimeError(f"Error uploading file to S3: {e}")

    def get_file(self, file_path: str) -> str:
        """Handles downloading of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            local_file_path = self._get_local_file_path(s3_key)
            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            return local_file_path
        except ClientError as e:
            raise RuntimeError(f"Error downloading file from S3: {e}")

    def delete_file(self, file_path: str) -> None:
        """Handles deletion of the file from S3 storage."""
        try:
            s3_key = self._extract_s3_key(file_path)
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except ClientError as e:
            raise RuntimeError(f"Error deleting file from S3: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_file(file_path)

    def delete_all_files(self) -> None:
        """Handles deletion of all files from S3 storage."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if "Contents" in response:
                for content in response["Contents"]:
                    # Skip objects that were not uploaded from the-finance-genie in the first place
                    if not content["Key"].startswith(self.key_prefix):
                        continue

                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=content["Key"]
                    )
        except ClientError as e:
            raise RuntimeError(f"Error deleting all files from S3: {e}")

        # Always delete from local storage
        LocalStorageProvider.delete_all_files()

    # The s3 key is the name assigned to an object. It excludes the bucket name, but includes the internal path and the file name.
    def _extract_s3_key(self, full_file_path: str) -> str:
        return "/".join(full_file_path.split("//")[1].split("/")[1:])

    def _get_local_file_path(self, s3_key: str) -> str:
        return f"{UPLOAD_DIR}/{s3_key.split('/')[-1]}"


def get_storage_provider(storage_provider: str):
    if storage_provider == "local":
        Storage = LocalStorageProvider()
    elif storage_provider == "s3":
        Storage = S3StorageProvider()
        raise RuntimeError(f"Unsupported storage provider: {storage_provider}")
    return Storage


Storage = get_storage_provider("local")
