from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage
from storages.backends.sftpstorage import SFTPStorage
from django.core.files.storage import FileSystemStorage


from poms_app import settings


def get_storage():
    storage = None

    if settings.SFTP_STORAGE_HOST:

        class SftpOverwriteStorage(SFTPStorage):
            """
            Custom file system storage: Overwrite get_available_name to make Django replace files instead of
            creating new ones over and over again.
            """
            def get_available_name(self, name, max_length=None):
                self.delete(name)
                return super().get_available_name(name, max_length)

        storage = SftpOverwriteStorage()

    if settings.AWS_S3_ACCESS_KEY_ID:

        class S3BotoOverwriteStorage(S3Boto3Storage):
            """
            Custom file system storage: Overwrite get_available_name to make Django replace files instead of
            creating new ones over and over again.
            """
            def get_available_name(self, name, max_length=None):
                self.delete(name)
                return super().get_available_name(name, max_length)

        storage = S3BotoOverwriteStorage()

    if settings.AZURE_ACCOUNT_KEY:

        class AzureOverwriteStorage(AzureStorage):
            """
            Custom file system storage: Overwrite get_available_name to make Django replace files instead of
            creating new ones over and over again.
            """
            def get_available_name(self, name, max_length=None):
                self.delete(name)
                return super().get_available_name(name, max_length)

        storage = AzureOverwriteStorage()

    if settings.USE_FILESYSTEM_STORAGE:

        class FileSystemOverwriteStorage(FileSystemStorage):
            """
            Custom file system storage: Overwrite get_available_name to make Django replace files instead of
            creating new ones over and over again.
            """
            def get_available_name(self, name, max_length=None):
                self.delete(name)
                return super().get_available_name(name, max_length)

        storage = FileSystemOverwriteStorage()


    return storage

