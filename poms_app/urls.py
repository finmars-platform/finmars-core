from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views import static
from poms.api.views import index
from django.views.generic import TemplateView
from poms.data_import.views import DataImportViewSet, DataImportSchemaViewSet

urlpatterns = []

urlpatterns += [
    url(r'^$', index, name='index'),
    url(r'^portal/', index, name='portal'),
    url(r'^import/add/', TemplateView.as_view(template_name='import_form.html'), name='import_add'),
    # url(r'^import/(?P<pk>\d+)/change/$', ImportUpdate.as_view(), name='import_change'),
    url(r'^api/', include('poms.api.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    if settings.DEBUG:
        urlpatterns += [
            url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
            url(r'^admin/', admin.site.urls),
        ]
    else:
        if settings.DEV:
            urlpatterns += [
                url(r'^411C74D6C4E24D2B98D6B085A580FF61/admin/doc/', include('django.contrib.admindocs.urls')),
            ]
        urlpatterns += [
            url(r'^411C74D6C4E24D2B98D6B085A580FF61/admin/', admin.site.urls),
        ]

# if settings.DEBUG:
#     if 'silk' in settings.INSTALLED_APPS:
#
#         urlpatterns += [
#             url(r'^silk/', include('silk.urls', namespace='silk'))
#         ]

if getattr(settings, 'MEDIA_SERVE', False):
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', static.serve, {'document_root': settings.MEDIA_ROOT})
    ]
