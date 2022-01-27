from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views import static

from healthcheck.views import HealthcheckView
from poms.api.views import index
from django.views.generic import TemplateView

urlpatterns = []

urlpatterns += [
    url(r'^$', index, name='index'),
    url(r'^'+ settings.BASE_API_URL + '/api/', include('poms.api.urls')),
    url(r'^'+ settings.BASE_API_URL + '/healthcheck', HealthcheckView.as_view()),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

if 'django.contrib.admin' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^'+ settings.BASE_API_URL + '/admin/', admin.site.urls),
    ]


