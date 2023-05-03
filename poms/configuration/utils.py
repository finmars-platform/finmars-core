import json
import logging
import os
import re
import zipfile

from django.apps import apps
from django.http import FileResponse
from django.core.files.base import ContentFile

from poms.common.storage import get_storage
from poms.common.utils import get_serializer, get_content_type_by_name

_l = logging.getLogger('poms.configuration')
storage = get_storage()


class DeleteFileAfterResponse(FileResponse):
    def __init__(self, *args, **kwargs):
        self.path_to_delete = kwargs.pop('path_to_delete', None)
        super().__init__(*args, **kwargs)

    def close(self):
        super().close()
        if self.path_to_delete:
            try:
                os.remove(self.path_to_delete)
            except FileNotFoundError:
                pass


def replace_special_chars_and_spaces(s):
    return re.sub(r'[^A-Za-z0-9]+', '_', s)

def remove_id_key_recursively(data):
    if not isinstance(data, dict):
        return data

    # Remove 'id' key if present
    data.pop('id', None)

    # Recursively process nested dictionaries
    for key, value in data.items():
        if isinstance(value, dict):
            remove_id_key_recursively(value)
        elif isinstance(value, list):
            for item in value:
                remove_id_key_recursively(item)

    return data

def user_code_to_file_name(configuration_code, user_code):
    try:
        code = user_code.split(configuration_code + ':')[1]

        return replace_special_chars_and_spaces(code).lower()

    except Exception as e:
        return replace_special_chars_and_spaces(user_code).lower()


def save_json_to_file(file_path, json_data):
    try:
        # Create the folder if it doesn't exist
        folder = os.path.dirname(file_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        _l.error('save_json_to_file %s: %s' % (file_path, e))

        raise Exception(e)


def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def zip_directory(source_dir, output_zipfile):
    with zipfile.ZipFile(output_zipfile, 'w', zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                archive.write(file_path, arcname=arcname)


def save_serialized_entity(content_type, configuration_code, source_directory, context):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise Exception("Could not find model for content type: %s" % content_type)

    dash = configuration_code + ':' + '-'

    filtered_objects = model.objects.filter(configuration_code=configuration_code).exclude(user_code=dash)

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        if 'is_deleted' in serialized_data:
            serialized_data.pop('is_deleted')

        if 'is_enabled' in serialized_data:
            serialized_data.pop('is_enabled')

        if 'deleted_user_code' in serialized_data:
            serialized_data.pop('deleted_user_code')

        path = source_directory + '/' + user_code_to_file_name(configuration_code, item.user_code) + '.json'

        save_json_to_file(path, serialized_data)


def save_serialized_attribute_type(content_type, configuration_code, content_type_key, source_directory, context):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise Exception("Could not find model for content type: %s" % content_type)

    entity_content_type = get_content_type_by_name(content_type_key)

    filtered_objects = model.objects.filter(configuration_code=configuration_code, content_type=entity_content_type)

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        # TODO convert content_type_id to content_type_key

        if 'deleted_user_code' in serialized_data:
            serialized_data.pop('deleted_user_code')

        path = source_directory + '/' + user_code_to_file_name(configuration_code, item.user_code) + '.json'

        save_json_to_file(path, serialized_data)


def save_serialized_layout(content_type, configuration_code, content_type_key, source_directory, context):
    try:
        model = apps.get_model(content_type)
    except Exception as e:
        raise Exception("Could not find model for content type: %s" % content_type)

    entity_content_type = get_content_type_by_name(content_type_key)

    _l.info('save_serialized_layout.entity_content_type %s' % entity_content_type)

    filtered_objects = model.objects.filter(configuration_code=configuration_code,
                                            content_type=entity_content_type,
                                            member=context['member'])

    _l.info('filtered_objects %s' % filtered_objects)

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = remove_id_key_recursively(serializer.data)

        path = source_directory + '/' + user_code_to_file_name(configuration_code, item.user_code) + '.json'

        save_json_to_file(path, serialized_data)


def unzip_to_directory(input_zipfile, output_directory):
    with zipfile.ZipFile(input_zipfile) as zf:
        zf.extractall(path=output_directory)


def list_json_files(directory):
    json_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    return json_files


def save_directory_to_storage(local_directory, storage_directory):
    for root, _, files in os.walk(local_directory):
        for file in files:
            local_path = os.path.join(root, file)

            # Calculate the destination path on S3
            relative_path = os.path.relpath(local_path, local_directory)
            s3_path = os.path.join(storage_directory, relative_path)

            # Save the file to S3
            with open(local_path, 'rb') as file_obj:
                storage.save(s3_path, file_obj)


def save_file_to_storage(file_path, storage_path):
    with open(file_path, 'rb') as file_obj:
        storage.save(storage_path, file_obj)


def copy_directory(src_dir, dst_dir):
    directories, files = storage.listdir(src_dir)

    # Copy files
    for file_name in files:
        src_file_path = os.path.join(src_dir, file_name)
        dst_file_path = os.path.join(dst_dir, file_name)

        with storage.open(src_file_path, 'rb') as src_file:
            content = src_file.read()
            with storage.open(dst_file_path, 'wb') as dst_file:
                dst_file.write(content)

    # Recursively copy subdirectories
    for directory in directories:
        src_subdir = os.path.join(src_dir, directory)
        dst_subdir = os.path.join(dst_dir, directory)

        if not storage.exists(dst_subdir):
            storage.makedirs(dst_subdir)

        copy_directory(src_subdir, dst_subdir)


def upload_directory_to_storage(local_directory, storage_directory):
    for root, dirs, files in os.walk(local_directory):
        for file in files:
            local_file_path = os.path.join(root, file)
            storage_file_path = os.path.join(storage_directory, os.path.relpath(local_file_path, local_directory))

            with open(local_file_path, 'rb') as local_file:
                content = local_file.read()
                storage.save(storage_file_path, ContentFile(content))