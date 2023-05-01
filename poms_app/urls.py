from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, include
from django.contrib import admin
from django.views import static

from django.views.static import serve
from healthcheck.views import HealthcheckView
from rest_framework.schemas import get_schema_view

from poms.api.views import serve_docs
from poms_app.openapi import get_redoc_urlpatterns

urlpatterns = []

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    urlpatterns += [
        # re_path(r'^' + settings.BASE_API_URL + '/admin/docs/', include('django.contrib.admindocs.urls')),
        re_path(r'^' + settings.BASE_API_URL + '/admin/', admin.site.urls),
    ]

urlpatterns += [
    re_path(r'^' + settings.BASE_API_URL + '/api/', include('poms.api.urls')),
    re_path(r'^' + settings.BASE_API_URL + '/healthcheck', HealthcheckView.as_view()),
]

if 'drf_yasg' in settings.INSTALLED_APPS:

    redoc_urlpatterns = get_redoc_urlpatterns()

    urlpatterns += redoc_urlpatterns

# if settings.ENABLE_DEV_DOCUMENTATION:
#     urlpatterns += [
#         re_path(r'^' + settings.BASE_API_URL + '/docs/(?P<path>.*)$', serve_docs, name='serve-docs')
#     ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      re_path(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns


