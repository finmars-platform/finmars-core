from tempfile import NamedTemporaryFile
from typing import Type

from django.db.models import Model


def vacuum_table(table: Type[Model]):
    table.objects.raw(f"VACUUM ANALYZE {table._meta.db_table}")


def get_local_path(filename: str) -> str:
    return f"/var/log/finmars/backend/{filename}.zip"


def get_storage_path(filename: str, space_code: str) -> str:
    return f"{space_code}/.system/history_files/{filename}.zip"


def save_to_local_file(file_path: str, buffer: bytes):
    with open(file_path, "wb") as output_file:
        output_file.write(buffer)


def save_to_remote_storage(storage, storage_path: str, buffer: bytes):
    with NamedTemporaryFile() as tmp_file:
        tmp_file.write(buffer)
        storage.save(storage_path, tmp_file)
