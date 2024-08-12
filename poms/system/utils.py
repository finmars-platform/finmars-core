import os

from django.conf import settings

DEFAULT_IMAGES_FOLDER = os.path.join(settings.BASE_DIR, "data")


def get_image_content(image_name: str) -> bytes:
    """
    Reads the content of an image file from the pre-defined folder 'data'
    in the project and returns it as bytes.
    Args:
        image_name (str): The name of the image file.
    Returns:
        bytes: The content of the image file.
    Raises:
        FileNotFoundError: If the image file does not exist.
        IOError: If there is an error reading the image file.
    """

    with open(os.path.join(DEFAULT_IMAGES_FOLDER, image_name), "rb") as file:
        return file.read()


def upload_default_logos_into_storage():
    """
    Uploads default logos from the pre-defined folder 'data' into the storage
    if the storage is configured.

    This function retrieves the storage object using the `get_storage` function
    from the `poms.common.storage` module. If the storage is configured, it checks
    if the default dark logo file and the default light logo file exist in the
    storage. If either of the files does not exist, it reads the content of the
    corresponding image file from the pre-defined folder 'data' in the project
    using the `get_image_content` function and saves it in the storage with the
    specified file paths. It then prints a message indicating the file path where
    the default logo file was saved.
    """
    from poms.common.storage import get_storage

    storage = get_storage()
    dark_log_path = ".system/ui/logo_dark.png"
    light_log_path = ".system/ui/logo_light.png"

    if storage:
        if not storage.exists(dark_log_path):
            storage.save(dark_log_path, get_image_content("logo_dark.png"))
            print(f"default logo file saved in {dark_log_path}")

        if not storage.exists(light_log_path):
            storage.save(light_log_path, get_image_content("logo_light.png"))
            print(f"default logo file saved in {light_log_path}")

    else:
        print("storage not configured, default logos not uploaded")
