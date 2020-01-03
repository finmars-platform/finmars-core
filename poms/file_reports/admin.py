from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import FileReport


class FileReportAdmin(admin.ModelAdmin):
    model = FileReport
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'type', 'name', 'notes', 'file_url']
    search_fields = ['id', 'name']
    raw_id_fields = ['master_user']

admin.site.register(FileReport, FileReportAdmin)
