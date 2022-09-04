from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, include
from django.contrib import admin
from django.views import static

from healthcheck.views import HealthcheckView
from poms.api.views import index
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

urlpatterns = []

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^' + settings.BASE_API_URL + '/admin/docs/', include('django.contrib.admindocs.urls')),
        re_path(r'^' + settings.BASE_API_URL + '/admin/', admin.site.urls),

    ]

urlpatterns += [
    re_path(r'^$', index, name='index'),
    re_path(r'^' + settings.BASE_API_URL + '/api/', include('poms.api.urls')),
    # re_path('openapi', get_schema_view(
    #     title="Finmars",
    #     description="Finmars API",
    #     version="1.0.0"
    # ), name='openapi-schema'),
    re_path(r'^' + settings.BASE_API_URL + '/healthcheck', HealthcheckView.as_view()),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      re_path(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns


