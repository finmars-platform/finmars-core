import os
import shutil
import tempfile
from zipfile import ZipFile

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

def _delete_azure_folder(azure_storage, folder_path):

    from azure.storage.blob import ContainerClient

    container_client = ContainerClient(account_url=azure_storage.account_url, container_name=azure_storage.azure_container, credential=azure_storage.account_key)

    # List all files in the folder
    blob_list = container_client.list_blobs(name_starts_with=folder_path)

    # Delete files in the folder
    for blob in blob_list:
        container_client.delete_blob(blob.name)


def _delete_s3_folder(s3_storage, folder_path):
    objects_to_delete = []

    # List all files in the folder
    for obj in s3_storage.bucket.objects.filter(Prefix=folder_path):
        objects_to_delete.append({"Key": obj.key})

    # Delete files in the folder
    if objects_to_delete:
        s3_storage.bucket.delete_objects(
            Delete={"Objects": objects_to_delete}
        )


def _delete_local_folder(path):
    shutil.rmtree(path)

def delete_folder(path):

    storage = get_storage()

    if settings.AZURE_ACCOUNT_KEY:
        _delete_azure_folder(storage, path)

    if settings.AWS_S3_ACCESS_KEY_ID:
        _delete_s3_folder(storage, path)

    if settings.USE_FILESYSTEM_STORAGE:
        _delete_local_folder(path)


def _download_s3_folder_as_zip(s3_storage, folder_path):
    # Create a temporary directory to store the downloaded files
    temp_dir = tempfile.mkdtemp()

    # Download all files from the remote folder to the temporary local directory
    for obj in s3_storage.bucket.objects.filter(Prefix=folder_path):
        local_path = os.path.join(temp_dir, os.path.relpath(obj.key, folder_path))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3_storage.bucket.download_file(obj.key, local_path)

    # Create a zip archive of the temporary local directory
    zip_file_path = f"{temp_dir}.zip"
    with ZipFile(zip_file_path, 'w') as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, temp_dir))

    # Clean up the temporary directory
    shutil.rmtree(temp_dir)

    return zip_file_path

def _download_azure_folder_as_zip(azure_storage, folder_path):

    from azure.storage.blob import ContainerClient
    temp_dir = tempfile.mkdtemp()

    # Download all files from the remote folder to the temporary local directory
    container_client = ContainerClient(account_url=azure_storage.account_url, container_name=azure_storage.azure_container, credential=azure_storage.account_key)
    blob_list = container_client.list_blobs(name_starts_with=folder_path)

    for blob in blob_list:
        local_path = os.path.join(temp_dir, os.path.relpath(blob.name, folder_path))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as local_file:
            blob_data = container_client.get_blob_client(blob.name).download_blob()
            blob_data.readinto(local_file)

def _download_local_folder_as_zip(folder_path):

    temp_dir = tempfile.mkdtemp()

    for root, _, files in os.walk(folder_path):
        for file in files:
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, folder_path)
            dst_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)

def download_folder_as_zip(path):

    storage = get_storage()

    if settings.AZURE_ACCOUNT_KEY:
        return _download_azure_folder_as_zip(storage, path)

    if settings.AWS_S3_ACCESS_KEY_ID:
        return _download_s3_folder_as_zip(storage, path)

    if settings.USE_FILESYSTEM_STORAGE:
        return _download_local_folder_as_zip(path)

    return None