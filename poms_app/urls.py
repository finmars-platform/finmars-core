from django.conf import settings
from django.contrib import admin
from django.urls import include, re_path
from healthcheck.views import HealthcheckView
from poms_app.openapi import get_redoc_urlpatterns

urlpatterns = []

if "django.contrib.admin" in settings.INSTALLED_APPS:
    urlpatterns = urlpatterns + [
        # re_path(r'^' + settings.BASE_API_URL + '/admin/docs/', include('django.contrib.admindocs.urls')),
        re_path(r"^(?P<space_code>[^/]+)/admin/", admin.site.urls),
        re_path(r"^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/admin/", admin.site.urls),
    ]

urlpatterns = urlpatterns + [

    # Old Approach (delete in 1.9.0)
    re_path(r"^(?P<space_code>[^/]+)/api/", include("poms.api.urls")),
    re_path(r"^(?P<space_code>[^/]+)/healthcheck", HealthcheckView.as_view()),
    re_path(r"^(?P<space_code>[^/]+)/healthz", HealthcheckView.as_view()), # needed for k8s healthcheck

    # New Approach
    re_path(r"^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/api/", include("poms.api.urls")),
    re_path(r"^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/healthcheck", HealthcheckView.as_view()),
    re_path(r"^(?P<realm_code>[^/]+)/(?P<space_code>[^/]+)/healthz", HealthcheckView.as_view()), # needed for k8s healthcheck
]

if "drf_yasg" in settings.INSTALLED_APPS:
    urlpatterns = urlpatterns + get_redoc_urlpatterns()

if settings.USE_DEBUGGER:
    import debug_toolbar

    urlpatterns = urlpatterns + [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ]

# if settings.ENABLE_DEV_DOCUMENTATION:
#     urlpatterns += [
#         re_path(r'^' + settings.BASE_API_URL + '/docs/(?P<path>.*)$', serve_docs, name='serve-docs')
#     ]
