from poms.common.admin import AbstractModelAdmin
from poms.explorer.models import FinmarsFile
from django.contrib import admin


@admin.register(FinmarsFile)
class FinmarsFileAdmin(AbstractModelAdmin):
    model = FinmarsFile
