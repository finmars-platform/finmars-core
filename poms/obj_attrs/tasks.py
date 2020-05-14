import time

from celery import shared_task

from poms.celery_tasks.models import CeleryTask
from poms.common.formula import safe_eval, ExpressionEvalError
from poms.common.utils import datetime_now
from poms.obj_attrs.models import GenericAttributeType, GenericAttribute

from logging import getLogger

_l = getLogger('poms.obj_attrs')

def get_attributes_as_obj(instance, target_model_content_type):

    result = {}

    attributes = GenericAttribute.objects.filter(object_id=instance.id, content_type=target_model_content_type)

    for attribute in attributes:

        attribute_type = attribute.attribute_type

        if attribute_type.value_type == 10:
            result[attribute_type.user_code] = attribute.value_string

        if attribute_type.value_type == 20:
            result[attribute_type.user_code] = attribute.value_float

        if attribute_type.value_type == 30:
            if attribute.classifier:
                result[attribute_type.user_code] = attribute.classifier.name
            else:
                result[attribute_type.user_code] = None

        if attribute_type.value_type == 40:
            result[attribute_type.user_code] = attribute.value_date

    return result

def get_json_objs(target_model, target_model_serializer, target_model_content_type, master_user, context):

    result = {}

    instances = target_model.objects.filter(master_user=master_user)

    for instance in instances:

        serializer = target_model_serializer(instance=instance, context=context)

        result[instance.id] = serializer.data

        result[instance.id]['attributes'] = get_attributes_as_obj(instance, target_model_content_type)

    return result


@shared_task(name='obj_attrs.recalculate_attributes', bind=True)
def recalculate_attributes(self, instance):

    _l.info('recalculate_attributes: instance', instance)
    # _l.info('recalculate_attributes: context', context)

    attribute_type = GenericAttributeType.objects.get(id=instance.attribute_type_id, master_user=instance.master_user)

    attributes = GenericAttribute.objects.filter(
        attribute_type=attribute_type,
        content_type=instance.target_model_content_type)

    _l.info('recalculate_attributes: attributes len %s' % len(attributes))
    _l.info('recalculate_attributes: attribute_type.expr %s' % attribute_type.expr)

    _l.info('self task id %s' % self.request.id)

    celery_task = CeleryTask.objects.create(master_user=instance.master_user,
                                            member=instance.member,
                                            started_at=datetime_now(),
                                            task_status='P',
                                            task_type='attribute_recalculation', task_id=self.request.id)

    celery_task.save()

    context = {
        'master_user': instance.master_user,
        'member': instance.member
    }

    json_objs = get_json_objs(instance.target_model,
                              instance.target_model_serializer,
                              instance.target_model_content_type,

                              instance.master_user,
                              context)

    total = len(attributes)
    current = 0

    for attr in attributes:

        data = json_objs[attr.object_id]

        # _l.info('data %s' % data)

        try:
            executed_expression = safe_eval(attribute_type.expr, names={'this': data}, context=context)
        except (ExpressionEvalError, TypeError, Exception, KeyError):
            executed_expression = 'Invalid Expression'

        # print('executed_expression %s' % executed_expression)

        if attr.attribute_type.value_type == GenericAttributeType.STRING:

            if executed_expression == 'Invalid Expression':
                attr.value_string = None
            else:
                attr.value_string = executed_expression

        if attr.attribute_type.value_type == GenericAttributeType.NUMBER:

            if executed_expression == 'Invalid Expression':
                attr.value_float = None
            else:
                attr.value_float = executed_expression

        if attr.attribute_type.value_type == GenericAttributeType.DATE:

            if executed_expression == 'Invalid Expression':
                attr.value_date = None
            else:
                attr.value_date = executed_expression

        if attr.attribute_type.value_type == GenericAttributeType.CLASSIFIER:

            if executed_expression == 'Invalid Expression':
                attr.classifier = None
            else:
                attr.classifier = executed_expression

        attr.save()

        current = current + 1

        celery_task.data = {
            "total_rows": total,
            "processed_rows": current
        }

        celery_task.save()

    celery_task.task_status = 'D'

    celery_task.save()
