from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.common.storage import get_storage
from poms.system.models import EcosystemConfiguration, WhitelabelModel

storage = get_storage()

STORAGE_ROOT = ".system/ui/"
THEME_CSS_FILE_PATH = f"{STORAGE_ROOT}theme.css"
LOGO_DARK_IMAGE_PATH = f"{STORAGE_ROOT}logo_dark.png"
LOGO_LIGHT_IMAGE_PATH = f"{STORAGE_ROOT}logo_light.png"
FAVICON_IMAGE_PATH = f"{STORAGE_ROOT}favicon.png"

MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100

COMMON_PREFIX = f"{settings.HOST_URL}/{{realm_code}}/{{space_code}}/api/storage/"


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
        prefix = COMMON_PREFIX.format(
            realm_code=self.context["realm_code"],
            space_code=self.context["space_code"],
        )

        theme_css_file = validated_data.pop("theme_css_file", None)
        if theme_css_file:
            storage.save(THEME_CSS_FILE_PATH, theme_css_file)
            validated_data["theme_css_url"] = f"{prefix}{THEME_CSS_FILE_PATH}"

        logo_dark_image = validated_data.pop("logo_dark_image", None)
        if logo_dark_image:
            storage.save(LOGO_DARK_IMAGE_PATH, logo_dark_image)
            validated_data["logo_dark_url"] = f"{prefix}{LOGO_DARK_IMAGE_PATH}"

        logo_light_image = validated_data.pop("logo_light_image", None)
        if logo_light_image:
            storage.save(LOGO_LIGHT_IMAGE_PATH, logo_light_image)
            validated_data["logo_light_url"] = f"{prefix}{LOGO_LIGHT_IMAGE_PATH}"

        favicon_image = validated_data.pop("favicon_image", None)
        if favicon_image:
            storage.save(FAVICON_IMAGE_PATH, favicon_image)
            validated_data["favicon_url"] = f"{prefix}{FAVICON_IMAGE_PATH}"

        return validated_data

    def create(self, validated_data: dict) -> WhitelabelModel:
        validated_data = self.change_files_to_urls(validated_data)
        return WhitelabelModel.objects.create(**validated_data)

    def update(
        self, instance: WhitelabelModel, validated_data: dict
    ) -> WhitelabelModel:
        validated_data = self.change_files_to_urls(validated_data)
        return super().update(instance, validated_data)


class WhitelabelListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhitelabelModel
        fields = "__all__"
