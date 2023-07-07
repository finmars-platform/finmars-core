import logging
import math
import os
import shutil
import tempfile
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage
from storages.backends.sftpstorage import SFTPStorage

from poms_app import settings

_l = logging.getLogger('poms.common')


def download_local_folder_as_zip(folder_path):
    zip_file_path = f"{folder_path}.zip"
    with ZipFile(zip_file_path, 'w') as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))

    return zip_file_path

class NamedBytesIO(BytesIO):
    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

class EncryptedStorage(object):

    def get_symmetric_key(self):

        if settings.ENCRYPTION_KEY:

            self.symmetric_key = bytes.fromhex(settings.ENCRYPTION_KEY)

        else:
            # TODO move from Encryption Key to Vault
            # TODO PROCEED ONLY AFTER NEW WAY OF SETTING UP SPACE IS READY
            try:

                # self.vault_client = Client(url='https://your-vault-url', token='your-vault-token')
                # Retrieve encryption and decryption keys from Vault
                self.symmetric_key = self._get_symmetric_key_from_vault()

            except Exception as e:
                raise Exception("Could not connect to Vault symmetric_key is not set. Error %s" % e)

    def _get_symmetric_key_from_vault(self):
        # Retrieve the symmetric key from Vault
        # TODO IMPLEMENT
        pass

    def _encrypt_file(self, file):
        # Encrypt the file content using the symmetric key
        file_content = file.read()

        # Generate a random nonce
        # You can generate a random nonce using os.urandom(12) for AES-256-GCM.
        # The recommended length for the nonce in AES-GCM is 12 bytes (96 bits).
        # Ensure that you securely store and associate the nonce with the encrypted data
        # so that you can use the same nonce during decryption.
        nonce = os.urandom(12)

        aesgcm = AESGCM(self.symmetric_key)
        encrypted_content = aesgcm.encrypt(nonce, file_content, None)

        encrypted_data = nonce + encrypted_content

        return ContentFile(encrypted_data)

    def _decrypt_file(self, file):
        # Decrypt the file content using the symmetric key

        encrypted_data = file.read()

        # Generate a random nonce
        # You can generate a random nonce using os.urandom(12) for AES-256-GCM.
        # The recommended length for the nonce in AES-GCM is 12 bytes (96 bits).
        # Ensure that you securely store and associate the nonce with the encrypted data
        # so that you can use the same nonce during decryption.
        # Extract the nonce from the encrypted data
        nonce = encrypted_data[:12]

        ciphertext = encrypted_data[12:]

        aesgcm = AESGCM(self.symmetric_key)
        decrypted_content = aesgcm.decrypt(nonce, ciphertext, None)

        # Create a file-like object from the decrypted content
        decrypted_file = NamedBytesIO(decrypted_content, name=file.name)

        return decrypted_file

    def open_skip_decrypt(self, name, mode='rb'):
        file = super()._open(name, mode)

        if settings.SERVER_TYPE == 'local':  # Do not decrypt on local server
            return file

        return file

    def _open(self, name, mode='rb'):
        # Open the file and decrypt its content
        file = super()._open(name, mode)

        if settings.SERVER_TYPE == 'local':  # Do not decrypt on local server
            return file

        return self._decrypt_file(file)

    def _save(self, name, content):
        # Encrypt the file content and save it

        if settings.SERVER_TYPE == 'local':  # Do not encrypt on local server
            return super()._save(name, content)

        encrypted_content = self._encrypt_file(content)
        return super()._save(name, encrypted_content)


class FinmarsStorage(EncryptedStorage):
    '''
    To ensure that storage overwrite passed filepath insead of appending a number to it
    '''

    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return super().get_available_name(name, max_length)

    def convert_size(self, size_bytes):
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def folder_exists_and_has_files(self, folder_path):
        # Ensure the folder path ends with a '/'
        if not folder_path.endswith('/'):
            folder_path += '/'

        try:  # TODO maybe wrong implementation
            if not self.listdir:
                raise NotImplemented("Listdir method not implemented")
            # Check if the folder exists by listing its contents
            files, folders = self.listdir(folder_path)

            # Return True if there are any files in the folder
            return bool(files)
        except Exception as e:
            return False

    def download_file_and_save_locally(self, storage_file_path, local_file_path):

        with self._open(storage_file_path, 'rb') as remote_file:
            # Read the file content
            file_content = remote_file.read()

        # Create directories in the local path if they do not exist
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        # Write the file content to the local file
        with open(local_file_path, 'wb') as local_file:
            local_file.write(file_content)

        return local_file_path

    def zip_directory(self, directory_path, zip_file_path):
        with ZipFile(zip_file_path, 'w', ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, directory_path)
                    zip_file.write(file_path, archive_path)

    def download_paths_as_zip(self, paths):

        zip_filename = 'archive.zip'

        temp_dir_path = os.path.join(os.path.dirname(zip_filename), 'tmp/temp_download')
        os.makedirs(temp_dir_path, exist_ok=True)

        for path in paths:
            local_filename = temp_dir_path + '/' + path
            if path.endswith('/'):  # Assuming the path is a directory

                if path[0] == '/':
                    self.download_directory(settings.BASE_API_URL + path, local_filename)
                else:
                    self.download_directory(settings.BASE_API_URL + '/' + path, local_filename)

            else:
                if path[0] == '/':
                    self.download_file_and_save_locally(settings.BASE_API_URL + path, local_filename)
                else:
                    self.download_file_and_save_locally(settings.BASE_API_URL + '/' + path, local_filename)

        self.zip_directory(temp_dir_path, zip_filename)

        # shutil.rmtree(temp_dir_path)

        return zip_filename


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

    def get_created_time(self, path):
        return self.get_modified_time(path)

    def delete_directory(self, directory_path):

        # List all files in the folder
        blob_list = self.client.list_blobs(name_starts_with=directory_path)

        # Delete files in the folder
        for blob in blob_list:
            self.client.delete_blob(blob.name)

    def download_directory(self, directory_path, local_destination_path):

        folder = os.path.dirname(local_destination_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        # Download all files from the remote folder to the temporary local directory

        blob_list = self.client.list_blobs(name_starts_with=directory_path)

        for blob in blob_list:
            # Check if the blob is inside the folder
            if blob.name.startswith(directory_path):
                local_path = os.path.join(local_destination_path, os.path.relpath(blob.name, directory_path))

                # Create the local directory structure
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download the blob to the local file
                blob_client = self.client.get_blob_client(blob.name)
                with open(local_path, "wb") as local_file:
                    download_stream = blob_client.download_blob()
                    local_file.write(download_stream.readall())

    def download_directory_as_zip(self, directory_path):

        # Download all files from the remote folder to the temporary local directory

        blob_list = self.client.list_blobs(name_starts_with=directory_path)

        temp_dir = tempfile.mkdtemp()

        for blob in blob_list:
            # Check if the blob is inside the folder
            if blob.name.startswith(directory_path):
                local_path = os.path.join(temp_dir, os.path.relpath(blob.name, directory_path))

                # Create the local directory structure
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download the blob to the local file
                blob_client = self.client.get_blob_client(blob.name)
                with open(local_path, "wb") as local_file:
                    download_stream = blob_client.download_blob()
                    local_file.write(download_stream.readall())

        # Create a zip archive of the temporary local directory
        zip_file_path = download_local_folder_as_zip(temp_dir)

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

        return zip_file_path


class FinmarsS3Storage(FinmarsStorage, S3Boto3Storage):

    def get_created_time(self, path):
        return self.get_modified_time(path)

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

        _l.info('directory_path %s' % directory_path)

        folder = os.path.dirname(local_destination_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        for obj in self.bucket.objects.filter(Prefix=directory_path):
            local_path = os.path.join(local_destination_path, os.path.relpath(obj.key, directory_path))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.bucket.download_file(obj.key, local_path)

    def download_directory_as_zip(self, directory_path):

        _l.info("S3 download zip")

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
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, directory_path))

    def download_directory(self, src, local_destination_path):
        # if not os.path.exists(local_destination_path):
        #     os.makedirs(local_destination_path, exist_ok=True)

        src_with_root = os.path.join(settings.MEDIA_ROOT, src)

        # shutil.copytree(src_with_root, local_destination_path, dirs_exist_ok=True)
        shutil.copytree(src_with_root, local_destination_path)

    def download_directory_as_zip(self, folder_path):
        path = os.path.join(settings.MEDIA_ROOT, folder_path)

        zip_file_path = download_local_folder_as_zip(path)
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

    if storage:
        storage.get_symmetric_key()  # IMPORTANT Storage MUST BE inherited from EncryptedStorage

    return storage
