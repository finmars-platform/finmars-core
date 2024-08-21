from typing import Optional

from django.core.files.base import File
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.storage import get_storage
from poms.system.models import EcosystemConfiguration, WhitelabelModel

storage = get_storage()

MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100

UI_ROOT = ".system/ui/"
URL_PREFIX = (
    f"https://{{host_url}}/{{realm_code}}/{{space_code}}/api/storage/{UI_ROOT}"
)


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


def validate_image_dimensions(value):
    width, height = get_image_dimensions(value)
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise ValidationError(
            f"Image dimensions {width}x{height} are too small. Image must be"
            f" at least {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels."
        )


class WhitelabelSerializer(serializers.ModelSerializer):
    theme_css_url = serializers.URLField(read_only=True)
    logo_dark_url = serializers.URLField(read_only=True)
    logo_light_url = serializers.URLField(read_only=True)
    favicon_url = serializers.URLField(read_only=True)
    #
    theme_css_file = serializers.FileField(
        required=False,
        validators=[FileExtensionValidator(["css"])],
    )
    logo_dark_image = serializers.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(["png", "jpg", "jpeg"]),
            validate_image_dimensions,
        ],
    )
    logo_light_image = serializers.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(["png", "jpg", "jpeg"]),
            validate_image_dimensions,
        ],
    )
    favicon_image = serializers.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(["png", "jpg", "jpeg"]),
            validate_image_dimensions,
        ],
    )

    class Meta:
        model = WhitelabelModel
        fields = [
            "id",
            "company_name",
            "theme_code",
            "theme_css_url",
            "logo_dark_url",
            "logo_light_url",
            "favicon_url",
            "custom_css",
            "is_default",
            #
            "theme_css_file",
            "logo_dark_image",
            "logo_light_image",
            "favicon_image",
        ]

    def change_files_to_urls(self, validated_data: dict) -> dict:
        """
        Change files to URLs in the validated data. Files will be saved, and their URLs
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
        api_prefix = URL_PREFIX.format(
            host_url=self.context["host_url"],
            realm_code=self.context["realm_code"],
            space_code=self.context["space_code"],
        )
        storage_prefix = f"{self.context['space_code']}/{UI_ROOT}"

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
                    api_prefix, storage_prefix, validated_data, file, model_field
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
        storage.save(f"{storage_prefix}{file.name}", file)
        validated_data[field] = f"{api_prefix}{file.name}"

    def create(self, validated_data: dict):
        validated_data = self.change_files_to_urls(validated_data)
        return WhitelabelModel.objects.create(**validated_data)

    def update(self, instance: WhitelabelModel, validated_data: dict):
        validated_data = self.change_files_to_urls(validated_data)
        return super().update(instance, validated_data)


class WhitelabelListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhitelabelModel
        fields = "__all__"
