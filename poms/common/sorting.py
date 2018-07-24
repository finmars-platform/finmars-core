from django.db.models import Case, When

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute


def sort_by_dynamic_attrs(request, queryset):
    ordering = request.GET.get('ordering')

    if ordering:

        print('sort_by_dynamic_attrs.ordering %s' % ordering)

        parts = ordering.split('___da_')

        if parts and len(parts) == 2:

            order = parts[0]
            key = parts[1]

            print('order %s' % order)
            print('key %s' % key)

            attribute_type = GenericAttributeType.objects.get(id__exact=key)

            attributes_queryset = GenericAttribute.objects.filter(attribute_type=attribute_type, object_id__in=queryset)

            print('attribute_type.value_type1 %s' % attribute_type.value_type)

            if order == '-':

                if attribute_type.value_type == 10:
                    attributes_queryset = attributes_queryset.order_by('-value_string')

                    print("Here desc?")

                if attribute_type.value_type == 20:
                    attributes_queryset = attributes_queryset.order_by('-value_float')

                if attribute_type.value_type == 30:
                    attributes_queryset = attributes_queryset.order_by('-classifier__name')

                if attribute_type.value_type == 40:
                    attributes_queryset = attributes_queryset.order_by('-value_date')

            else:

                if attribute_type.value_type == 10:
                    attributes_queryset = attributes_queryset.order_by('value_string')

                    print("Here asc?")

                if attribute_type.value_type == 20:
                    attributes_queryset = attributes_queryset.order_by('value_float')

                if attribute_type.value_type == 30:
                    attributes_queryset = attributes_queryset.order_by('classifier__name')

                if attribute_type.value_type == 40:
                    attributes_queryset = attributes_queryset.order_by('value_date')

            print('attributes_queryset %s' % attributes_queryset)

            # TODO refactor!

            result = []

            for a in attributes_queryset:

                for i in queryset:

                    if a.object_id == i.id:
                        result.append(i)



            print(result)

            queryset = result

    print(queryset)

    return queryset
