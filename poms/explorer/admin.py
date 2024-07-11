from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.explorer.models import FinmarsDirectory, FinmarsFile, ShareAccessRecord


@admin.register(FinmarsFile)
class FinmarsFileAdmin(AbstractModelAdmin):
    model = FinmarsFile


@admin.register(FinmarsDirectory)
class FinmarsDirAdmin(AbstractModelAdmin):
    model = FinmarsDirectory


@admin.register(ShareAccessRecord)
class FinmarsDirAdmin(AbstractModelAdmin):
    model = ShareAccessRecord
