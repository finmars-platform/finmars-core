from __future__ import unicode_literals

from poms.obj_perms.serializers import ModelWithObjectPermissionSerializer
from poms.reference_tables.models import ReferenceTableRow, ReferenceTable
from poms.users.fields import MasterUserField
from rest_framework import serializers


class ReferenceTableRowSerializer(serializers.ModelSerializer):

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = ReferenceTableRow
        fields = [
            'id', 'key', 'value'
        ]


class ReferenceTableSerializer(serializers.ModelSerializer):
    master_user = MasterUserField()

    rows = ReferenceTableRowSerializer(many=True)

    class Meta(ModelWithObjectPermissionSerializer.Meta):
        model = ReferenceTable
        fields = [
            'id', 'master_user', 'name', 'rows'
        ]

    def set_rows(self, instance, rows):

        ReferenceTableRow.objects.filter(reference_table=instance.id).delete()

        for row in rows:
            ReferenceTableRow.objects.create(reference_table=instance, **row)


    def create(self, validated_data):

        rows = validated_data.pop('rows')
        instance = ReferenceTable.objects.create(**validated_data)

        self.set_rows(instance=instance, rows=rows)

        return instance

    def update(self, instance, validated_data):

        rows = validated_data.pop('rows')

        instance.name = validated_data.get('name', instance.name)

        self.set_rows(instance=instance, rows=rows)

        instance.save()

        return instance
