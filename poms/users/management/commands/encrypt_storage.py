import os
import traceback

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from poms.common.storage import get_storage


class Command(BaseCommand):
    help = 'Encrypts all files in storage'

    def handle(self, *args, **options):
        # Generate a new symmetric key
        symmetric_key = bytes.fromhex(settings.ENCRYPTION_KEY)

        storage = get_storage()
        # Save the keys to Vault or any other secure storage
        # You can use the Vault client or any other library to store the keys securely

        # Encrypt files recursively
        try:
            self.encrypt_files_recursively(storage, symmetric_key, settings.BASE_API_URL)
        except Exception as e:
            print('Error encrypting files: %s ' % traceback.format_exc())
            print('Error encrypting files: %s' % e)

        self.stdout.write(self.style.SUCCESS('All files have been encrypted.'))

    def encrypt_files_recursively(self, storage, symmetric_key, directory):
        files = storage.listdir(directory)[1]
        for file_name in files:


            file_path = os.path.join(directory, file_name)

            print("File_path %s" % file_path )

            file = storage.open(file_path, 'rb')
            file_content = file.read()
            aesgcm = AESGCM(symmetric_key)
            nonce = os.urandom(12)
            encrypted_content = aesgcm.encrypt(nonce, file_content, None)
            encrypted_file = ContentFile(encrypted_content)
            storage.save(file_path, encrypted_file)



        # Encrypt files within subdirectories
        subdirectories = storage.listdir(directory)[0]
        for subdirectory in subdirectories:

            print(f"subdirectory {subdirectory_path}")

            subdirectory_path = os.path.join(directory, subdirectory)
            self.encrypt_files_recursively(storage, symmetric_key, subdirectory_path)
