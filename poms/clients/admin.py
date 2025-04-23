from django.contrib import admin
from poms.common.admin import ClassModelAdmin
from poms.clients.models import Client

admin.site.register(Client, ClassModelAdmin)
