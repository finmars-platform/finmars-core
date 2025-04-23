from django.db.models import Prefetch

from poms.obj_attrs.models import GenericAttribute, GenericAttributeType


def get_attr_type_view_perms(model_cls):
    codename_set = [
        "view_%(model_name)s",
        "change_%(model_name)s",
        "manage_%(model_name)s",
    ]
    kwargs = {
        "app_label": model_cls._meta.app_label,
        "model_name": model_cls._meta.model_name,
    }
    return {perm % kwargs for perm in codename_set}


def get_attributes_prefetch(path="attributes"):
    return Prefetch(
        path,
        queryset=GenericAttribute.objects.select_related(
            "attribute_type",
        ).prefetch_related(
            "attribute_type__options",
            "attribute_type__classifiers",
        ),
    )


def get_attributes_prefetch_simple(path="attributes"):
    return Prefetch(
        path,
        queryset=GenericAttribute.objects.select_related(
            "attribute_type",
        ).prefetch_related(
            "attribute_type__options",
            "attribute_type__classifiers",
        ),
    )
