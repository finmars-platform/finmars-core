import json
import logging
import os
import zipfile

from django.apps import apps
from django.http import FileResponse

from poms.common.utils import get_serializer, get_content_type_by_name

_l = logging.getLogger('poms.configuration')


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

    filtered_objects = model.objects.filter(configuration_code=configuration_code)

    SerializerClass = get_serializer(content_type)

    for item in filtered_objects:
        serializer = SerializerClass(item, context=context)
        serialized_data = serializer.data

        path = source_directory + '/' + item.user_code + '.json'

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
        serialized_data = serializer.data

        path = source_directory + '/' + item.user_code + '.json'

        save_json_to_file(path, serialized_data)
