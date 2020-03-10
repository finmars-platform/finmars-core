from django.contrib import admin

# Register your models here.
from poms.schedules.models import PricingSchedule


class PricingScheduleAdmin(admin.ModelAdmin):
    model = PricingSchedule
    list_display = ['id', 'master_user', 'name', 'user_code', 'cron_expr', 'next_run_at', 'last_run_at']
    raw_id_fields = ['master_user']
    filter_horizontal = ['pricing_procedures']


admin.site.register(PricingSchedule, PricingScheduleAdmin)