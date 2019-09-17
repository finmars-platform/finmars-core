from django.contrib.messages.storage.base import BaseStorage, Message
from django.contrib.messages.storage.cookie import CookieStorage as DjangoCookieStorage
from django.contrib.messages.storage.fallback import FallbackStorage as DjangoFallbackStorage
from django.utils import timezone
from django.utils.encoding import force_text

from poms.notifications.models import Notification


# Can user is null  middleware process_response if used in Rest Framework authtoken?

class DbStorage(BaseStorage):
    def _get(self, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            queryset = Notification.objects.filter(read_date__isnull=True)
            ret = []
            for n in queryset:
                message = Message(n.level, force_text(n), None)
                message.id = n.pk
                ret.append(message)
                # print(0, getattr(message, 'id', None), message)
            return ret, True
        else:
            return [], False

    def _store(self, messages, response, *args, **kwargs):
        user = self.request.user
        if messages:
            if user.is_authenticated:
                for message in messages:
                    if not hasattr(message, 'id'):
                        Notification.objects.create(recipient=user, level=message.level, message=message)
        else:
            Notification.objects.filter(recipient=user, read_date__isnull=True).update(read_date=timezone.now())
        return []


class CookieStorage(DjangoCookieStorage):
    def _get(self, *args, **kwargs):
        messages, all_retrieved = super(CookieStorage, self)._get(*args, **kwargs)
        return messages, False


class FallbackStorage(DjangoFallbackStorage):
    storage_classes = (CookieStorage, DbStorage)
