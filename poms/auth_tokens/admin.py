from django.contrib import admin

from poms.auth_tokens.models import AuthToken


class AuthTokenAdmin(admin.ModelAdmin):
    model = AuthToken
    list_display = [
        "id",
        "user",
        "key",
        "current_master_user",
        "current_member",
    ]
    raw_id_fields = ["user"]


admin.site.register(AuthToken, AuthTokenAdmin)
