from django.core.files.storage import FileSystemStorage
from poms_app import settings

from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage
from storages.backends.sftpstorage import SFTPStorage


def get_storage():
    storage = None

    if settings.SFTP_STORAGE_HOST:
        storage = SFTPStorage()

    if settings.AWS_S3_ACCESS_KEY_ID:
        storage = S3Boto3Storage()

    if settings.AZURE_ACCOUNT_KEY:
        storage = AzureStorage()

    if settings.USE_FILESYSTEM_STORAGE:
        storage = FileSystemStorage()

    return storage
