from logging import getLogger

_l = getLogger('poms.integrations')

# @receiver(pre_save, dispatch_uid='pricing_automated_schedule_reschedule', sender=PricingAutomatedSchedule)
# def pricing_automated_schedule_reschedule(sender, instance=None, **kwargs):
#     # from djcelery.models import CrontabSchedule, PeriodicTask
#     if instance.is_enabled and instance.next_run_at < timezone.now():
#         instance.schedule(save=False)
