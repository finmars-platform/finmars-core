import json
from logging import getLogger

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db import models
from django.utils.translation import gettext_lazy

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
        encoded_text = text.encode("utf-8")
        file_url = self._get_path(file_name)
        try:
            if storage:
                storage.save(
                    f"/{master_user.space_code}{file_url}",
                    ContentFile(encoded_text),
                )

            else:  # local/test mode
                print(f"file '{file_name}' content '{text}' saved to storage '{file_url}'")

        except Exception as e:
            _l.error(f"upload_file {file_name} {file_url} error {repr(e)}")
            return ""

        self.file_url = file_url
        return file_url

    def upload_json_as_local_file(self, file_name, dict_to_json, master_user):
        file_url = self._get_path(file_name)
        try:
            if storage:
                with storage.open(f"/{master_user.space_code}{file_url}", "w") as fp:
                    json.dump(dict_to_json, fp, indent=4, default=str)

            else:
                with open(file_name, "w") as fp:
                    json.dump(dict_to_json, fp, indent=4, default=str)

        except Exception as e:
            _l.error(f"upload_file {file_url} error {repr(e)}")
            return ""

        self.file_url = file_url
        return file_url

    def get_file(self):
        result = None

        if storage:
            path = self.file_url
            if not path:
                path = self.master_user.space_code
            elif path[0] == "/":
                path = self.master_user.space_code + path
            else:
                path = f"{self.master_user.space_code}/{path}"
            try:
                with storage.open(path, "rb") as f:
                    result = f.read()

            except Exception as e:
                _l.error(f"Cant open file {self.file_name} {self.file_url} due to {repr(e)}")

        else:  # local mode
            with open(self.file_name, "rt") as f:
                result = f.read()

        return result

    @staticmethod
    def _get_path(file_name):
        return f"/.system/file_reports/{file_name}"

    def send_emails(self, emails: list):
        if not emails:
            return

        email = EmailMessage(
            subject=f"Report {self.name} file {self.file_name}",
            body=f"Please find the attached report {self.name} file {self.file_name}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails,
        )

        content = self.get_file()
        if content:
            email.attach(filename=self.file_name, content=content)
            email.send(fail_silently=True)
