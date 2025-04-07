from datetime import date, datetime
from decimal import Decimal
from json import JSONEncoder

from django.conf import settings
from django.db.models import QuerySet
from rest_framework.renderers import JSONRenderer

_DATE_FORMAT = settings.API_DATE_FORMAT
_TIME_FORMAT = settings.API_TIME_FORMAT


class ExtendedJSONEncoder(JSONEncoder):
    """
    Extended JSON encoder with custom handling for:
    - date & datetime objects
    - Decimals objects (to be converted to string)
    - Django QuerySets

    Attention! float inf, -inf & nan will cause ValueError exception
    """

    def __init__(self, *args, **kwargs):
        kwargs["allow_nan"] = False
        super().__init__(*args, **kwargs)

    def default(self, obj):
        obj_type = type(obj)

        if obj_type is datetime:
            return obj.strftime(_TIME_FORMAT)

        if obj_type is date:
            return obj.strftime(_DATE_FORMAT)

        if isinstance(obj, QuerySet):
            return list(obj.values())

        if obj_type is Decimal:
            return float(obj)

        return super().default(obj)


class FinmarsJSONRenderer(JSONRenderer):
    encoder_class = ExtendedJSONEncoder
