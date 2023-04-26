from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, include
from django.contrib import admin
from django.views import static

from django.views.static import serve
from healthcheck.views import HealthcheckView
from rest_framework.schemas import get_schema_view

from poms.api.views import serve_docs

urlpatterns = []

# if 'django.contrib.admin' in settings.INSTALLED_APPS:
#     urlpatterns += [
#         re_path(r'^' + settings.BASE_API_URL + '/admin/docs/', include('django.contrib.admindocs.urls')),
#         re_path(r'^' + settings.BASE_API_URL + '/admin/', admin.site.urls),
#
#     ]

urlpatterns += [
    re_path(r'^' + settings.BASE_API_URL + '/api/', include('poms.api.urls')),
    re_path(r'^' + settings.BASE_API_URL + '/healthcheck', HealthcheckView.as_view()),
]

if 'drf_yasg' in settings.INSTALLED_APPS:

    from rest_framework import permissions
    from drf_yasg.views import get_schema_view
    from drf_yasg import openapi

    import poms.accounts.urls as account_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/accounts/', include(account_router.router.urls)),
    ]

    schema_view = get_schema_view(
        openapi.Info(
            title="Finmars API",
            default_version='v1',
            description="Finmars Documentation",
            terms_of_service="https://www.finmars.com/policies/terms/",
            contact=openapi.Contact(email="admin@finmars.com"),
            license=openapi.License(name="BSD License"),
            x_logo={
                "url": "https://landing.finmars.com/wp-content/uploads/2023/04/logo.png",
                "backgroundColor": "#000",
                "href": '/' + settings.BASE_API_URL + '/docs/'
            }
        ),
        patterns=local_urlpatterns,
        public=True,
        permission_classes=[permissions.AllowAny],
    )

    urlpatterns += [
        # re_path(r'^' + settings.BASE_API_URL + '/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
        # re_path(r'^' + settings.BASE_API_URL + '/swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]

# if settings.ENABLE_DEV_DOCUMENTATION:
#     urlpatterns += [
#         re_path(r'^' + settings.BASE_API_URL + '/docs/(?P<path>.*)$', serve_docs, name='serve-docs')
#     ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      re_path(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns


