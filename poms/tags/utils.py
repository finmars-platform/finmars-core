from django.db.models import Q, Prefetch
from django.utils.encoding import force_text

from poms.obj_perms.utils import get_permissions_prefetch_lookups
from poms.tags.models import TagLink, Tag


def filter_by_tag_name(queryset, value):
    if value:
        tags = force_text(value).split(',')
        f = Q()
        for t in tags:
            f |= Q(tags__name__istartswith=t)
        return queryset.filter(f)
    return queryset


def tags_prefetch(queryset):
    return queryset.prefetch_related(
        'tags',
        # 'tags__user_object_permissions',
        # 'tags__user_object_permissions__permission',
        'tags__group_object_permissions',
        'tags__group_object_permissions__permission',
    )


def get_tag_prefetch(path='tags'):
    return Prefetch(
        path,
        queryset=TagLink.objects.select_related(
            'tag'
        ).prefetch_related(
            'content_object',
            # *get_permissions_prefetch_lookups(
            #     ('tag', Tag)
            # )
        )
    )
