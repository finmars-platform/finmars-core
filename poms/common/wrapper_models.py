from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType

from poms.common.models import NamedModel
from poms.integrations.models import ProviderClass


class NamedModelAutoMapping(NamedModel):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(self)
        provider = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)
        value = self.user_code

        if not value:
            value = self.name

        master_user = self.master_user

        modelName = content_type.model + 'mapping'

        model = ContentType.objects.get(app_label='integrations', model=modelName).model_class()

        super(NamedModelAutoMapping, self).save(*args, **kwargs)

        # if not model.objects.filter(value=value, content_object=self, provider=provider,
        #                             master_user=master_user).exists():
        #
        #     model.objects.create(value=value, content_object=self, provider=provider,
        #                          master_user=master_user)
