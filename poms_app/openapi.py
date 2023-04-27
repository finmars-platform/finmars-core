from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.urls import re_path, include
from django.shortcuts import render



def generate_schema(local_urlpatterns):

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
                "href": '/' + settings.BASE_API_URL + '/docs/api/v1/'
            }
        ),
        patterns=local_urlpatterns,
        public=True,
        permission_classes=[permissions.AllowAny],
    )

    return schema_view


def get_account_documentation():

    import poms.accounts.urls as account_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/accounts/', include(account_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view

def get_portfolio_documentation():

    import poms.portfolios.urls as portfolio_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/portfolio/', include(portfolio_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view

def get_currency_documentation():

    import poms.currencies.urls as currency_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/currency/', include(currency_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def render_main_page(request):

    context = {
        'space_code': settings.BASE_API_URL
    }

    return render(request, 'finmars_redoc.html', context)

def get_redoc_urlpatterns():

    account_schema_view = get_account_documentation()
    portfolio_schema_view = get_portfolio_documentation()
    currency_schema_view = get_currency_documentation()



    urlpatterns = [

        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/$', render_main_page, name='main'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/account', account_schema_view.with_ui('redoc', cache_timeout=0), name='account'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/portfolio', portfolio_schema_view.with_ui('redoc', cache_timeout=0), name='portfolio'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/currency', currency_schema_view.with_ui('redoc', cache_timeout=0), name='currency'),


    ]

    return urlpatterns