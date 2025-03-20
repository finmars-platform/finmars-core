from typing import Optional
from urllib.parse import quote

from django.core.files.base import File
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.serializers import ModelMetaSerializer, ModelWithUserCodeSerializer
from poms.common.storage import get_storage
from poms.system.models import EcosystemConfiguration, WhitelabelModel

storage = get_storage()

MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100
MAX_FILENAME_LENGTH = 1024

CHARS_TO_AVOID = "&$@=;/:+,?\\{^}%`]><['\"~#|"

UI_ROOT = ".system/ui"
URL_PREFIX = f"api/storage/{UI_ROOT}"


class EcosystemConfigurationSerializer(serializers.ModelSerializer):
    data = serializers.JSONField(allow_null=False)

    class Meta:
        model = EcosystemConfiguration
        fields = [
            "id",
            "name",
            "description",
            "data",
        ]


def validate_image_dimensions(image):
    width, height = get_image_dimensions(image)
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise ValidationError(
            f"Image dimensions {width}x{height} are too small. Image must be"
            f" at least {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels"
        )

def has_bad_symbols(file_name: str) -> bool:
    return any(c in CHARS_TO_AVOID for c in file_name)


def validate_file_name(file: File):
    file_name = file.name
    try:
        file_name.encode("utf-8")
    except UnicodeEncodeError as e:
        raise ValidationError("Filename is not a valid UTF-8 string") from e

    if len(file_name) > MAX_FILENAME_LENGTH:
        raise ValidationError(
            f"Filename '{file_name}' is too long, max length is {MAX_FILENAME_LENGTH}"
        )

    if has_bad_symbols(file_name):
        raise ValidationError(
            f"Filename '{file_name}' contains invalid symbols: {CHARS_TO_AVOID}"
        )

    return file


class WhitelabelSerializer(ModelWithUserCodeSerializer, ModelMetaSerializer):
    theme_css_url = serializers.URLField(read_only=True)
    logo_dark_url = serializers.URLField(read_only=True)
    logo_light_url = serializers.URLField(read_only=True)
    favicon_url = serializers.URLField(read_only=True)
    
    theme_css_file = serializers.FileField(
        required=False,
        validators=[
            FileExtensionValidator(["css"]),
            validate_file_name,
        ],
    )
    logo_dark_image = serializers.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(["png", "jpg", "jpeg"]),
            validate_file_name,
            validate_image_dimensions,
        ],
    )
    logo_light_image = serializers.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(["png", "jpg", "jpeg"]),
            validate_file_name,
            validate_image_dimensions,
        ],
    )
    favicon_image = serializers.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(["png", "jpg", "jpeg"]),
            validate_file_name,
            validate_image_dimensions,
        ],
    )

    class Meta:
        model = WhitelabelModel
        fields = [
            "id",
            "name",
            "user_code",
            "configuration_code",
            "notes",

            "theme_css_url",
            "logo_dark_url",
            "logo_light_url",
            "favicon_url",
            "custom_css",
            "is_default",

            "theme_css_file",
            "logo_dark_image",
            "logo_light_image",
            "favicon_image",

            "company_name",
            "theme_code",
        ]

    def change_files_to_path(self, validated_data: dict) -> dict:
        """
        Change files to path in the validated data. Files will be saved, and their path
        in the Django storage will be inserted in the validated data.
        Args:
            validated_data (dict): The validated data containing
            the files to be converted to URLs.
        Returns:
            dict: The updated validated data with URLs.
        Note:
            - The function assumes that the context contains the keys "realm_code"
              and "space_code".
            - The function assumes that the storage module has a save method
              that takes in a file path and a file object.
        """
        storage_prefix = f"{self.context['request'].user.master_user.space_code}/{UI_ROOT}"

        params_fields = [
            ("theme_css_file", "theme_css_url"),
            ("logo_dark_image", "logo_dark_url"),
            ("logo_light_image", "logo_light_url"),
            ("favicon_image", "favicon_url"),
        ]

        for param_name, model_field in params_fields:
            file: Optional[File] = validated_data.pop(param_name, None)
            if file:
                self.save_to_storage(
                    URL_PREFIX, storage_prefix, validated_data, file, model_field
                )

        return validated_data

    @staticmethod
    def save_to_storage(
        api_prefix: str,
        storage_prefix: str,
        validated_data: dict,
        file: File,
        field: str,
    ):
        storage.save(f"{storage_prefix}/{file.name}", file)
        validated_data[field] = f"{api_prefix}/{quote(file.name)}"

    def create(self, validated_data: dict):
        validated_data = self.change_files_to_path(validated_data)
        return super().create(validated_data)

    def update(self, instance: WhitelabelModel, validated_data: dict):
        validated_data = self.change_files_to_path(validated_data)
        return super().update(instance, validated_data)
