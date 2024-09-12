from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.explorer.models import StorageObject


@admin.register(StorageObject)
class FinmarsDirAdmin(AbstractModelAdmin):
    model = StorageObject
