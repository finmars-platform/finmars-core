import math
from collections import OrderedDict

from django.views.generic.dates import timezone_today
from django.utils.timezone import now

import copy


def force_qs_evaluation(qs):
    list(qs)

    pass

    # for item in qs:
    #     pass


def db_class_check_data(model, verbosity, using):
    from django.db import IntegrityError, ProgrammingError

    try:
        exists = set(model.objects.using(using).values_list('pk', flat=True))
    except ProgrammingError:
        return
    if verbosity >= 2:
        print('existed transaction classes -> %s' % exists)
    for id, code, name in model.CLASSES:
        if id not in exists:
            if verbosity >= 2:
                print('create %s class -> %s:%s' % (model._meta.verbose_name, id, name))
            try:
                model.objects.using(using).create(pk=id, system_code=code,
                                                  name_en=name, description_en=name)
            except (IntegrityError, ProgrammingError):
                pass
        else:
            obj = model.objects.using(using).get(pk=id)
            obj.system_code = code
            if not obj.name_en:
                obj.name_en = name
            if not obj.description_en:
                obj.description_en = name
            obj.save()


def date_now():
    return timezone_today()

def datetime_now():
    return now()

try:
    isclose = math.isclose
except AttributeError:
    try:
        import numpy

        isclose = numpy.isclose
    except ImportError:
        numpy = None


        def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
            # TODO: maybe incorrect!
            return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def iszero(v):
    return isclose(v, 0.0)


# def safe_div(a, b, default=0.0):
#     try:
#         return a / b
#     except (ZeroDivisionError, TypeError):
#         return default


class sfloat(float):
    def __truediv__(self, other):
        # print('__truediv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__truediv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rtruediv__(self, other):
        # print('__rtruediv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__rtruediv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __floordiv__(self, other):
        # print('__floordiv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__floordiv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rfloordiv__(self, other):
        # print('__floordiv__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__rfloordiv__(other)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __pow__(self, power):
        # print('__pow__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__pow__(power)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def __rpow__(self, power):
        # print('__rpow__: self=%s, other=%s' % (self, other))
        try:
            return super(sfloat, self).__rpow__(power)
        except (ZeroDivisionError, OverflowError):
            return 0.0


def add_view_and_manage_permissions():
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission

    existed = {(p.content_type_id, p.codename) for p in Permission.objects.all()}
    for content_type in ContentType.objects.all():
        codename = "view_%s" % content_type.model
        if (content_type.id, codename) not in existed:
            Permission.objects.update_or_create(
                content_type=content_type, codename=codename,
                defaults={
                    'name': 'Can view %s' % content_type.name
                }
            )

        codename = "manage_%s" % content_type.model
        if (content_type.id, codename) not in existed:
            Permission.objects.update_or_create(
                content_type=content_type, codename=codename,
                defaults={
                    'name': 'Can manage %s' % content_type.name
                }
            )


def delete_keys_from_dict(dict_del, the_keys):
    """
    Delete the keys present in the lst_keys from the dictionary.
    Loops recursively over nested dictionaries.
    """
    # make sure the_keys is a set to get O(1) lookups
    if type(the_keys) is not set:
        the_keys = set(the_keys)
    for k, v in dict_del.items():

        if k in the_keys:
            del dict_del[k]

        if isinstance(v, dict):
            delete_keys_from_dict(v, the_keys)
    return dict_del


def recursive_callback(dict, callback, prop="children"):
    callback(dict)

    print(dict)

    if prop in dict:
        for item in dict[prop]:
            recursive_callback(item, callback)


class MemorySavingQuerysetIterator(object):

    def __init__(self,queryset,max_obj_num=1000):
        self._base_queryset = queryset
        self._generator = self._setup()
        self.max_obj_num = max_obj_num

    def _setup(self):
        for i in range(0,self._base_queryset.count(),self.max_obj_num):
            # By making a copy of of the queryset and using that to actually access
            # the objects we ensure that there are only `max_obj_num` objects in
            # memory at any given time
            smaller_queryset = copy.deepcopy(self._base_queryset)[i:i+self.max_obj_num]
            # logger.debug('Grabbing next %s objects from DB' % self.max_obj_num)
            for obj in smaller_queryset.iterator():
                yield obj

    def __iter__(self):
        return self

    def next(self):
        return self._generator.next()


def format_float(val):

    # 0.000050000892 -> 0.0000500009
    # 0.005623 -> 0.005623
    # 0.005623000551 -> 0.0056230006

    try:
        float(val)
    except ValueError:
        return val

    return float(format(round(val, 10), '.10f').rstrip("0").rstrip('.'))


def format_float_to_2(val):

    # 0.000050000892 -> 0.0000500009
    # 0.005623 -> 0.005623
    # 0.005623000551 -> 0.0056230006

    try:
        float(val)
    except ValueError:
        return val

    return float(format(round(val, 2), '.2f').rstrip("0").rstrip('.'))
