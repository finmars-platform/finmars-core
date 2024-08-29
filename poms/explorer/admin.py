from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.explorer.models import FinmarsDirectory


@admin.register(FinmarsDirectory)
class FinmarsDirAdmin(AbstractModelAdmin):
    model = FinmarsDirectory
