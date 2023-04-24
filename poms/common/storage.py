import os
import shutil
import tempfile
from zipfile import ZipFile

from django.core.files.storage import FileSystemStorage
from poms_app import settings

from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage
from storages.backends.sftpstorage import SFTPStorage

import logging
_l = logging.getLogger('poms.common')

def download_local_folder_as_zip(folder_path):

    temp_dir = tempfile.mkdtemp()

    for root, _, files in os.walk(folder_path):
        for file in files:
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, folder_path)
            dst_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.copy2(src_path, dst_path)

class FinmarsStorage(object):

    '''
    To ensure that storage overwrite passed filepath insead of appending a number to it
    '''
    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return super().get_available_name(name, max_length)

class FinmarsSFTPStorage(FinmarsStorage, SFTPStorage):

    def delete_directory(self, directory_path):
        for root, _, files in self.sftp_client.walk(directory_path):
            for file in files:
                self.sftp_client.remove(os.path.join(root, file))

    def download_directory(self, directory_path, local_destination_path):
        folder = os.path.dirname(local_destination_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        for root, _, files in self.sftp_client.walk(directory_path):
            for file in files:
                remote_path = os.path.join(root, file)
                local_path = os.path.join(local_destination_path, os.path.relpath(remote_path, directory_path))
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                self.sftp_client.get(remote_path, local_path)

class FinmarsAzureStorage(FinmarsStorage, AzureStorage):

    def delete_directory(self, directory_path):

        from azure.storage.blob import ContainerClient

        container_client = ContainerClient(account_url=self.account_url, container_name=self.azure_container, credential=self.account_key)

        # List all files in the folder
        blob_list = container_client.list_blobs(name_starts_with=directory_path)

        # Delete files in the folder
        for blob in blob_list:
            container_client.delete_blob(blob.name)

    def download_directory(self, directory_path, local_destination_path):

        folder = os.path.dirname(local_destination_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        from azure.storage.blob import ContainerClient

        # Download all files from the remote folder to the temporary local directory
        container_client = ContainerClient(account_url=self.account_url, container_name=self.azure_container, credential=self.account_key)
        blob_list = container_client.list_blobs(name_starts_with=directory_path)

        for blob in blob_list:
            # Check if the blob is inside the folder
            if blob.name.startswith(directory_path):
                local_path = os.path.join(local_destination_path, os.path.relpath(blob.name, directory_path))

                # Create the local directory structure
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download the blob to the local file
                blob_client = container_client.get_blob_client(blob.name)
                with open(local_path, "wb") as local_file:
                    download_stream = blob_client.download_blob()
                    local_file.write(download_stream.readall())

    def download_directory_as_zip(self, directory_path):

        from azure.storage.blob import ContainerClient

        # Download all files from the remote folder to the temporary local directory
        container_client = ContainerClient(account_url=self.account_url, container_name=self.azure_container, credential=self.account_key)
        blob_list = container_client.list_blobs(name_starts_with=directory_path)

        temp_dir = tempfile.mkdtemp()

        for blob in blob_list:
            # Check if the blob is inside the folder
            if blob.name.startswith(directory_path):
                local_path = os.path.join(temp_dir, os.path.relpath(blob.name, directory_path))

                # Create the local directory structure
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download the blob to the local file
                blob_client = container_client.get_blob_client(blob.name)
                with open(local_path, "wb") as local_file:
                    download_stream = blob_client.download_blob()
                    local_file.write(download_stream.readall())

        # Create a zip archive of the temporary local directory
        zip_file_path = download_local_folder_as_zip(temp_dir)

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

        return zip_file_path


class FinmarsS3Storage(FinmarsStorage, S3Boto3Storage):

    def delete_directory(self, directory_path):

        objects_to_delete = []

        # List all files in the folder
        for obj in self.bucket.objects.filter(Prefix=directory_path):
            objects_to_delete.append({"Key": obj.key})

        # Delete files in the folder
        if objects_to_delete:
            self.bucket.delete_objects(
                Delete={"Objects": objects_to_delete}
            )

    def download_directory(self, directory_path, local_destination_path):

        folder = os.path.dirname(local_destination_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        for obj in self.bucket.objects.filter(Prefix=directory_path):
            local_path = os.path.join(local_destination_path, os.path.relpath(obj.key, directory_path))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.bucket.download_file(obj.key, local_path)

    def download_directory_as_zip(self, directory_path):

        temp_dir = tempfile.mkdtemp()

        # Download all files from the remote folder to the temporary local directory
        for obj in self.bucket.objects.filter(Prefix=directory_path):
            local_path = os.path.join(temp_dir, os.path.relpath(obj.key, directory_path))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.bucket.download_file(obj.key, local_path)

        # Create a zip archive of the temporary local directory
        zip_file_path = download_local_folder_as_zip(temp_dir)

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

        return zip_file_path


class FinmarsLocalFileSystemStorage(FinmarsStorage, FileSystemStorage):

    def delete_directory(self, directory_path):

        shutil.rmtree(directory_path)

    def download_directory(self, directory_path, local_destination_path):

        folder = os.path.dirname(local_destination_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        shutil.copytree(directory_path, local_destination_path)

    def download_directory_as_zip(self, folder_path):

        zip_file_path = f"{folder_path}.zip"
        with ZipFile(zip_file_path, 'w') as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, folder_path))

        return zip_file_path



def get_storage():
    storage = None

    if settings.SFTP_STORAGE_HOST:

        storage = FinmarsSFTPStorage()


    if settings.AWS_S3_ACCESS_KEY_ID:

        storage = FinmarsS3Storage()

    if settings.AZURE_ACCOUNT_KEY:

        storage = FinmarsAzureStorage()


    if settings.USE_FILESYSTEM_STORAGE:

        storage = FinmarsLocalFileSystemStorage()

    return storage





