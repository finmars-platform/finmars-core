import traceback
import json
from logging import getLogger

from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy

from poms_app import settings

from poms.common.storage import get_storage

storage = get_storage()


_l = getLogger("poms.file_reports")


class FileReport(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    master_user = models.ForeignKey(
        "users.MasterUser",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    file_url = models.TextField(  # probably deprecated
        blank=True,
        default="",
        verbose_name=gettext_lazy("File URL"),
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=gettext_lazy("notes"),
    )
    content_type = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    def upload_file(self, file_name, text, master_user):
        file_url = self._get_path(master_user, file_name)

        try:
            encoded_text = text.encode("utf-8")

            storage.save(
                f"/{settings.BASE_API_URL}{file_url}",
                ContentFile(encoded_text),
            )

        except Exception as e:
            _l.info(f"upload_file error {repr(e)} {traceback.format_exc()}")

        self.file_url = file_url

        # _l.info(f"FileReport.upload_file.file_url {file_url}")

        return file_url

    def upload_json_as_local_file(self, file_name, dict_to_json, master_user):
        file_url = self._get_path(master_user, file_name)

        try:
            with storage.open(f"/{settings.BASE_API_URL}{file_url}", 'w') as fp:
                json.dump(dict_to_json, fp, indent=4, default=str)

        except Exception as e:
            _l.info(f"upload_file error {repr(e)} {traceback.format_exc()}")

        self.file_url = file_url

        # _l.info(f"FileReport.upload_file.file_url {file_url}")

        return file_url
    

    def get_file(self):
        result = None

        # print(f"get_file self.file_url {self.file_url}")

        path = self.file_url

        if not path:
            path = settings.BASE_API_URL
        elif path[0] == "/":
            path = settings.BASE_API_URL + path
        else:
            path = f"{settings.BASE_API_URL}/{path}"

        try:
            with storage.open(path, "rb") as f:
                result = f.read()

        except Exception as e:
            print(f"Cant open file Exception: {repr(e)}")

        return result

    def _get_path(self, master_user, file_name):
        return f"/.system/file_reports/{file_name}"
