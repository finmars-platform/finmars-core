from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str
from rest_framework.fields import ReadOnlyField
from rest_framework.relations import PrimaryKeyRelatedField, RelatedField

from poms.common.fields import SlugRelatedFilteredField, UserCodeOrPrimaryKeyRelatedField, \
    PrimaryKeyRelatedFilteredField
from poms.transactions.filters import TransactionTypeInputContentTypeFilter
from poms.transactions.models import TransactionType, TransactionTypeGroup, TransactionTypeInput
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.utils import get_member_from_context, get_master_user_from_context


class TransactionTypeGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = TransactionTypeGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionTypeField(PrimaryKeyRelatedFilteredField):
    queryset = TransactionType.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class TransactionTypeInputField(RelatedField):
    queryset = TransactionTypeInput.objects

    def get_queryset(self):
        qs = super(TransactionTypeInputField, self).get_queryset()
        return qs

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            if isinstance(data, str):
                return queryset.get(name=data)
            else:
                return queryset.get(pk=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name='name', value=str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return getattr(obj, 'id')


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
            self.fail('does_not_exist', slug_name=self.slug_field, value=force_str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return '%s.%s' % (obj.app_label, obj.model)


class ReadOnlyContentTypeField(ReadOnlyField):
    def __init__(self, **kwargs):
        super(ReadOnlyContentTypeField, self).__init__(**kwargs)

    def to_representation(self, obj):
        return '%s.%s' % (obj.app_label, obj.model)
