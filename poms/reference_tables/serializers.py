from __future__ import unicode_literals

from rest_framework import serializers

from poms.common.serializers import ModelWithUserCodeSerializer, ModelWithTimeStampSerializer, ModelMetaSerializer
from poms.reference_tables.models import ReferenceTableRow, ReferenceTable
from poms.users.fields import MasterUserField
from poms.users.utils import get_member_from_context


class ReferenceTableRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceTableRow
        fields = [
            'id', 'key', 'value', 'order'
        ]


class ReferenceTableSerializer(ModelWithUserCodeSerializer, ModelWithTimeStampSerializer, ModelMetaSerializer):
    master_user = MasterUserField()

    rows = ReferenceTableRowSerializer(many=True)

    class Meta:
        model = ReferenceTable
        fields = [
            'id', 'master_user',
            'name', 'user_code', 'configuration_code',
            'rows'
        ]

    def set_rows(self, instance, rows):
        ReferenceTableRow.objects.filter(reference_table=instance.id).delete()

        for row in rows:
            ReferenceTableRow.objects.create(reference_table=instance, **row)

    def create(self, validated_data):
        rows = validated_data.pop('rows')

        member = get_member_from_context(self.context)

        instance = ReferenceTable.objects.create(**validated_data, owner=member)

        self.set_rows(instance=instance, rows=rows)

        return instance

    def update(self, instance, validated_data):
        rows = validated_data.pop('rows')

        instance.name = validated_data.get('name', instance.name)

        member = get_member_from_context(self.context)
        instance.owner = member

        self.set_rows(instance=instance, rows=rows)

        instance.save()

        return instance
