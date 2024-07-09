import logging
import math
import os
import shutil
import tempfile
from io import BytesIO
from zipfile import ZipFile

from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage
from storages.backends.sftpstorage import SFTPStorage

from poms_app import settings

_l = logging.getLogger("poms.common")


def download_local_folder_as_zip(folder_path):
    zip_file_path = f"{folder_path}.zip"
    with ZipFile(zip_file_path, "w") as zipf:
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
                raise Exception(
                    f"Could not connect to Vault symmetric_key is not set. Error {e}"
                )

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

        # Create a ContentFile with the decrypted content
        decrypted_file = ContentFile(decrypted_content)

        return File(decrypted_file, name=file.name)

    def open_skip_decrypt(self, name, mode="rb"):
        return super()._open(name, mode)

    def _open(self, name, mode="rb"):
        # Open the file and decrypt its content
        file = super()._open(name, mode)

        return file if settings.SERVER_TYPE == "local" else self._decrypt_file(file)

    def _save(self, name, content):
        # Encrypt the file content and save it

        if settings.SERVER_TYPE == "local":  # Do not encrypt on local server
            return super()._save(name, content)

        encrypted_content = self._encrypt_file(content)
        return super()._save(name, encrypted_content)


class FinmarsStorage(EncryptedStorage):
    """
    To ensure that storage overwrite passed filepath insead of appending a number to it
    """

    def save(self, name, content, max_length=None):
        """
        Save new content to the file specified by name. The content should be
        a proper File object or any Python file-like object, ready to be read
        from the beginning.
        """
        # Get the proper name for the file, as it will actually be saved.
        if name is None:
            name = content.name

        if not hasattr(content, "chunks"):
            content = File(content, name)

        name = self.get_available_name(name, max_length=max_length)
        name = self._save(name, content)
        # Ensure that the name returned from the storage system is still valid.
        # validate_file_name(name, allow_relative_path=True) # TODO Not needed
        return name

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
        if not folder_path.endswith("/"):
            folder_path += "/"

        try:  # TODO maybe wrong implementation
            if not self.listdir:
                raise NotImplemented("Listdir method not implemented")
            # Check if the folder exists by listing its contents
            dirs, files = self.listdir(folder_path)

            _l.info('folder_path %s' % folder_path)
            _l.info('files %s' % files)
            _l.info('folders %s' % dirs)

            # Return True if there are any files in the folder
            return bool(files)
        except Exception as e:
            _l.error(f"folder_exists_and_has_files exception: {e}")
            return False

    def download_file_and_save_locally(self, storage_file_path, local_file_path):
        with self._open(storage_file_path, "rb") as remote_file:
            # Read the file content
            file_content = remote_file.read()

        # Create directories in the local path if they do not exist
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        # Write the file content to the local file
        with open(local_file_path, "wb") as local_file:
            local_file.write(file_content)

        return local_file_path

    def zip_directory(self, paths, output_zip_path):
        # _l.info('zip_directory.paths %s' % paths)
        # _l.info('zip_directory.output_zip_path %s' % output_zip_path)

        with ZipFile(output_zip_path, "w") as zf:
            for path in paths:
                # If the path is a file, simply add it to the root of the zip archive
                if os.path.isfile(path):
                    zf.write(path, arcname=os.path.basename(path))

                # If the path is a directory, add its contents to the root of the zip archive
                elif os.path.isdir(path):
                    for foldername, subfolders, filenames in os.walk(path):
                        for filename in filenames:
                            full_path = os.path.join(foldername, filename)

                            # Adjusting the relative_path calculation to add the directory's contents
                            # directly to the root of the zip archive
                            base_dir = os.path.basename(path)
                            relative_path = os.path.relpath(
                                full_path, os.path.dirname(path)
                            )
                            if relative_path.startswith(base_dir):
                                relative_path = relative_path[len(base_dir) + 1 :]

                            zf.write(full_path, arcname=relative_path)

    def download_directory_content_as_zip(self, path_to_directory):
        from poms.users.models import MasterUser

        unique_path_prefix = os.urandom(32).hex()

        temp_dir_path = os.path.join(
            f"{settings.BASE_DIR}/tmp/temp_download/{unique_path_prefix}"
        )
        os.makedirs(temp_dir_path, exist_ok=True)

        local_filename = temp_dir_path

        master_user = MasterUser.objects.all().first()
        # TODO REFACTOR HERE
        # get space_code somewhere else
        self.download_directory(
            master_user.space_code + path_to_directory, local_filename
        )

        output_zip_filename = os.path.join(
            settings.BASE_DIR
            + "/tmp/temp_download/%s" % (unique_path_prefix + "_archive.zip")
        )

        self.zip_directory([temp_dir_path], output_zip_filename)
        # shutil.rmtree(temp_dir_path)

        return output_zip_filename

    def download_paths_as_zip(self, paths):
        from poms.users.models import MasterUser

        unique_path_prefix = os.urandom(32).hex()

        temp_dir_path = os.path.join(
            f"{settings.BASE_DIR}/tmp/temp_download/{unique_path_prefix}"
        )
        os.makedirs(temp_dir_path, exist_ok=True)

        _l.info(f"temp_dir_path {temp_dir_path}  paths {paths}")

        master_user = MasterUser.objects.all().first()
        # TODO REFACTOR HERE
        # get space_code somewhere else

        for path in paths:
            local_filename = temp_dir_path

            _l.info("path %s" % path)
            _l.info("local_filename %s" % local_filename)

            if path.endswith("/"):  # Assuming the path is a directory
                local_filename = f"{local_filename}/" + path.split("/")[-2]

                if path[0] == "/":
                    self.download_directory(
                        master_user.space_code + path, local_filename
                    )
                else:
                    self.download_directory(
                        master_user.space_code + "/" + path, local_filename
                    )

            else:
                local_filename = f"{local_filename}/" + path.split("/")[-1]

                # local_filename = local_filename  + '/' + path.split('/')[-1]

                _l.info("local_filename %s " % local_filename)

                if path[0] == "/":
                    self.download_file_and_save_locally(
                        master_user.space_code + path, local_filename
                    )
                else:
                    self.download_file_and_save_locally(
                        master_user.space_code + "/" + path, local_filename
                    )

        output_zip_filename = os.path.join(
            settings.BASE_DIR
            + "/tmp/temp_download/%s" % (unique_path_prefix + "_archive.zip")
        )

        self.zip_directory([temp_dir_path], output_zip_filename)
        # shutil.rmtree(temp_dir_path)

        return output_zip_filename


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
                local_path = os.path.join(
                    local_destination_path, os.path.relpath(remote_path, directory_path)
                )
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
                local_path = os.path.join(
                    local_destination_path, os.path.relpath(blob.name, directory_path)
                )

                # Create the local directory structure
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download the blob to the local file
                with open(local_path, "wb") as local_file, self.open(
                    blob.name
                ) as download_stream:
                    local_file.write(download_stream.read())

    def download_directory_as_zip(self, directory_path):
        # Download all files from the remote folder to the temporary local directory

        blob_list = self.client.list_blobs(name_starts_with=directory_path)

        temp_dir = tempfile.mkdtemp()

        for blob in blob_list:
            # Check if the blob is inside the folder
            if blob.name.startswith(directory_path):
                local_path = os.path.join(
                    temp_dir, os.path.relpath(blob.name, directory_path)
                )

                # Create the local directory structure
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                # Download the blob to the local file
                with open(local_path, "wb") as local_file, self.open(
                    blob.name
                ) as download_stream:
                    local_file.write(download_stream.read())

        # Create a zip archive of the temporary local directory
        zip_file_path = download_local_folder_as_zip(temp_dir)

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

        return zip_file_path


class FinmarsS3Storage(FinmarsStorage, S3Boto3Storage):
    def get_created_time(self, path):
        return self.get_modified_time(path)

    def delete_directory(self, directory_path):
        objects_to_delete = [
            {"Key": obj.key}
            for obj in self.bucket.objects.filter(Prefix=directory_path)
        ]
        # Delete files in the folder
        if objects_to_delete:
            self.bucket.delete_objects(Delete={"Objects": objects_to_delete})

    def download_directory(self, directory_path, local_destination_path):
        _l.info("Starting download from S3 directory: %s", directory_path)
        _l.info("Local destination path: %s", local_destination_path)

        # Ensure the local destination path exists
        os.makedirs(local_destination_path, exist_ok=True)

        # Iterate over all objects with the specified prefix
        for obj in self.bucket.objects.filter(Prefix=directory_path):
            # Construct the local file path
            local_file_path = os.path.join(
                local_destination_path, os.path.relpath(obj.key, directory_path)
            )
            _l.info("Processing object: %s", obj.key)

            # Skip if the object is a directory (ends with '/')
            if obj.key.endswith("/"):
                # Create the directory structure locally
                os.makedirs(local_file_path, exist_ok=True)
            else:
                # Ensure the local directory for the file exists
                local_file_dir = os.path.dirname(local_file_path)
                os.makedirs(local_file_dir, exist_ok=True)

                # Open the S3 object and write its content to the local file
                try:
                    with open(local_file_path, "wb") as local_file:
                        with self.open(obj.key) as s3_file:
                            # Read the S3 file in chunks
                            for chunk in iter(lambda: s3_file.read(4096), b""):
                                local_file.write(chunk)
                except Exception as e:
                    _l.error(
                        "Failed to download %s to %s: %s", obj.key, local_file_path, e
                    )
                    continue  # Skip this file and continue with the next one

        _l.info("Download completed successfully.")

    def download_directory_as_zip(self, directory_path):
        _l.info("S3 download zip")

        temp_dir = tempfile.mkdtemp()

        # Download all files from the remote folder to the temporary local directory
        # for obj in self.bucket.objects.filter(Prefix=directory_path):
        #     local_path = os.path.join(temp_dir, os.path.relpath(obj.key, directory_path))
        #     os.makedirs(os.path.dirname(local_path), exist_ok=True)
        #     self.bucket.download_file(obj.key, local_path)

        for obj in self.bucket.objects.filter(Prefix=directory_path):
            if obj.key != directory_path:  # Exclude the directory itself
                local_path = os.path.join(
                    temp_dir, os.path.relpath(obj.key, directory_path)
                )
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as local_file, self.open(
                    obj.key
                ) as s3_file:
                    local_file.write(s3_file.read())

        # Create a zip archive of the temporary local directory
        zip_file_path = download_local_folder_as_zip(temp_dir)

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

        return zip_file_path

    def dir_exists(self, path: str) -> bool:
        if not path.endswith("/"):
            raise ValueError("dir path must ends with /")

        try:
            dirs, files = self.listdir(path)
            if dirs or files:
                return True

            return self.size(path[:-1]) == 0

        except Exception as e:
            _l.error(f"dir_exists: check resulted in {repr(e)}")
            return False


class FinmarsLocalFileSystemStorage(FinmarsStorage, FileSystemStorage):
    def path(self, name):
        if name[0] == "/":
            return settings.MEDIA_ROOT + name

        return f"{settings.MEDIA_ROOT}/{name}"

    def listdir(self, path):
        path = self.path(path)
        directories, files = [], []
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_dir():
                    directories.append(entry.name)
                else:
                    files.append(entry.name)
        return directories, files

    def delete_directory(self, directory_path):
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, directory_path))

    def download_directory(self, src, local_destination_path):
        # if not os.path.exists(local_destination_path):
        #     os.makedirs(local_destination_path, exist_ok=True)

        # src_with_root = os.path.join(settings.MEDIA_ROOT, src)
        #
        # # shutil.copytree(src_with_root, local_destination_path, dirs_exist_ok=True)
        # shutil.copytree(src_with_root, local_destination_path)

        # _l.info('download_directory. src %s' % src)
        # _l.info('download_directory. local_destination_path %s' % local_destination_path)

        directory_content = self.listdir(src)
        _l.info(directory_content)

        directories = directory_content[0]
        files = directory_content[1]

        for file in files:
            path = src + file if src.endswith("/") else f"{src}/{file}"
            # _l.info('download_directory file . file %s' % file)
            # _l.info('download_directory path . path %s' % path)

            self.download_file_and_save_locally(
                path, os.path.join(local_destination_path, file)
            )

            # _l.info('download_directory.path %s' % path)

        for directory in directories:
            path = src + directory if src.endswith("/") else f"{src}/{directory}"
            self.download_directory(
                path, os.path.join(local_destination_path, directory)
            )

    def download_directory_as_zip(self, folder_path):
        path = os.path.join(settings.MEDIA_ROOT, folder_path)

        return download_local_folder_as_zip(path)


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
        # IMPORTANT! Storage MUST BE inherited from EncryptedStorage
        storage.get_symmetric_key()

    return storage
