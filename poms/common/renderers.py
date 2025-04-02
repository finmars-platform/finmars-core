from datetime import date, datetime
from json import JSONEncoder

from rest_framework.renderers import JSONRenderer


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        """
        Custom handling of NaN, Infinity, -Infinity, date and datetime objects.
        """
        if isinstance(obj, float) and (obj != obj or obj in {float("inf"), float("-inf")}):
            return None

        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")

        return super().default(obj)


class CustomJSONRenderer(JSONRenderer):
    encoder_class = CustomJSONEncoder
