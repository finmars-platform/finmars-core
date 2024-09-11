from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.explorer.models import FinmarsDirectory, FinmarsFile


@admin.register(FinmarsFile)
class FinmarsFileAdmin(AbstractModelAdmin):
    model = FinmarsFile


@admin.register(FinmarsDirectory)
class FinmarsDirAdmin(AbstractModelAdmin):
    model = FinmarsDirectory
