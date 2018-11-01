from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_text
from rest_framework.fields import ReadOnlyField
from rest_framework.relations import PrimaryKeyRelatedField

from poms.common.fields import SlugRelatedFilteredField
from poms.obj_perms.fields import PrimaryKeyRelatedFilteredWithObjectPermissionField
from poms.obj_perms.utils import obj_perms_filter_objects_for_view
from poms.transactions.filters import TransactionTypeInputContentTypeFilter
from poms.transactions.models import TransactionType, TransactionTypeGroup, TransactionTypeInput
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.utils import get_member_from_context, get_master_user_from_context


class TransactionTypeGroupField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = TransactionTypeGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionTypeField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = TransactionType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionTypeInputField(PrimaryKeyRelatedField):
    queryset = TransactionTypeInput.objects

    def get_queryset(self):
        qs = super(TransactionTypeInputField, self).get_queryset()

        master_user = get_master_user_from_context(self.context)
        qs = qs.filter(transaction_type__master_user=master_user)

        member = get_member_from_context(self.context)
        tt_qs = obj_perms_filter_objects_for_view(member, TransactionType.objects.filter(master_user=master_user))
        # queryset = ObjectPermissionFilter().simple_filter_queryset(member, queryset)
        return qs.filter(transaction_type__in=tt_qs)


# class TransactionClassifierField(AttributeClassifierBaseField):
#     queryset = TransactionClassifier.objects
#
#
# class TransactionAttributeTypeField(PrimaryKeyRelatedFilteredField):
#     queryset = TransactionAttributeType.objects
#     filter_backends = [
#         OwnerByMasterUserFilter,
#         ObjectPermissionBackend,
#     ]


class TransactionTypeInputContentTypeField(SlugRelatedFilteredField):
    queryset = ContentType.objects
    filter_backends = [
        TransactionTypeInputContentTypeFilter
    ]

    def __init__(self, **kwargs):
        kwargs['slug_field'] = 'model'
        super(TransactionTypeInputContentTypeField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:

            app_label, model = data.split('.')

            return self.get_queryset().get(app_label=app_label, model=model)

        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name=self.slug_field, value=smart_text(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return '%s.%s' % (obj.app_label, obj.model)


class ReadOnlyContentTypeField(ReadOnlyField):
    def __init__(self, **kwargs):
        super(ReadOnlyContentTypeField, self).__init__(**kwargs)

    def to_representation(self, obj):
        return '%s.%s' % (obj.app_label, obj.model)
