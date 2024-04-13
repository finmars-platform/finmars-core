from django.conf import settings
from django.contrib import admin
from django.urls import include, re_path, path
from healthcheck.views import HealthcheckView
from poms_app.openapi import get_redoc_urlpatterns

urlpatterns = []

if "django.contrib.admin" in settings.INSTALLED_APPS:

    urlpatterns = urlpatterns + [
        # re_path(r'^' + settings.BASE_API_URL + '/admin/docs/', include('django.contrib.admindocs.urls')),
        # re_path(r"^" + settings.REALM_CODE + "/admin/", admin.site.urls),
        re_path(rf"^{settings.REALM_CODE}/(?:space\w{{5}})/admin/", admin.site.urls),
    ]

urlpatterns = urlpatterns + [

    path("<slug:realm_code>/<slug:space_code>/api/", include("poms.api.urls")),
    path("<slug:realm_code>/<slug:space_code>/healthcheck/", HealthcheckView.as_view()),
    path("<slug:realm_code>/<slug:space_code>/healthz/", HealthcheckView.as_view()), # needed for k8s healthcheck

]

if "drf_yasg" in settings.INSTALLED_APPS:
    urlpatterns = urlpatterns + get_redoc_urlpatterns()

if settings.USE_DEBUGGER:
    import debug_toolbar

    urlpatterns = urlpatterns + [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ]

if settings.SERVER_TYPE == "local":
    import debug_toolbar

    urlpatterns += [
        re_path("__debug__/", include(debug_toolbar.urls)),
    ]

    urlpatterns += [
        re_path(
            r"^dev/auth/", include("rest_framework.urls", namespace="rest_framework")
        ),
    ]