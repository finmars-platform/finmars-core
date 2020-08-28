from django.contrib import admin


from poms.credentials.models import Credentials


class CredentialsAdmin(admin.ModelAdmin):
    model = Credentials
    list_display = ['id', 'master_user', 'name', 'user_code', 'type', 'provider', 'created', 'modified']
    raw_id_fields = ['master_user']


admin.site.register(Credentials, CredentialsAdmin)

