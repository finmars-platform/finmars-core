from datetime import date, datetime
from json import JSONEncoder

from django.conf import settings
from rest_framework.renderers import JSONRenderer


class ExtendedJSONEncoder(JSONEncoder):
    def default(self, obj):
        """
        Custom handling of NaN, Infinity, -Infinity, date and datetime objects.
        """
        if isinstance(obj, float) and (obj != obj or obj in {float("inf"), float("-inf")}):
            return None

        if isinstance(obj, datetime):
            return obj.strftime(settings.API_TIME_FORMAT)

        if isinstance(obj, date):
            return obj.strftime(settings.API_DATE_FORMAT)

        return super().default(obj)


class FinmarsJSONRenderer(JSONRenderer):
    encoder_class = ExtendedJSONEncoder
