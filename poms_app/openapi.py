from django.conf import settings
from django.shortcuts import render
from django.urls import re_path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


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
                "url": "https://finmars.com/wp-content/uploads/2023/04/logo.png",
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
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/portfolios/', include(portfolio_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_currency_documentation():
    import poms.currencies.urls as currency_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/currencies/', include(currency_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_instrument_documentation():
    import poms.instruments.urls as instrument_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/instruments/', include(instrument_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_transaction_documentation():
    import poms.transactions.urls as transaction_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/transactions/', include(transaction_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_counterparty_documentation():
    import poms.counterparties.urls as counterparty_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/counterparties/', include(counterparty_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_strategy_documentation():
    import poms.strategies.urls as strategy_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/strategies/', include(strategy_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_report_documentation():
    import poms.reports.urls as report_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/reports/', include(report_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_procedure_documentation():
    import poms.procedures.urls as procedure_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/procedures/', include(procedure_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_ui_documentation():
    import poms.ui.urls as ui_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/ui/', include(ui_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_explorer_documentation():
    import poms.explorer.urls as explorer_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/explorer/', include(explorer_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_import_documentation():
    import poms.integrations.urls as integrations_router
    import poms.csv_import.urls as csv_import_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/import/', include(integrations_router.router.urls)),
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/import/', include(csv_import_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_iam_documentation():
    import poms.iam.urls as iam_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/iam/', include(iam_router.router.urls)),
    ]

    schema_view = generate_schema(local_urlpatterns)

    return schema_view


def get_vault_documentation():
    import poms.vault.urls as vault_router

    local_urlpatterns = [
        re_path(r'^' + settings.BASE_API_URL + '/api/v1/vault/', include(vault_router.router.urls)),
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
    instrument_schema_view = get_instrument_documentation()
    transaction_schema_view = get_transaction_documentation()
    counterparty_schema_view = get_counterparty_documentation()
    strategy_schema_view = get_strategy_documentation()
    report_schema_view = get_report_documentation()
    procedure_schema_view = get_procedure_documentation()
    ui_schema_view = get_ui_documentation()
    explorer_schema_view = get_explorer_documentation()
    import_schema_view = get_import_documentation()
    iam_schema_view = get_iam_documentation()
    vault_schema_view = get_vault_documentation()

    urlpatterns = [

        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/$', render_main_page, name='main'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/account',
                account_schema_view.with_ui('redoc', cache_timeout=0), name='account'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/portfolio',
                portfolio_schema_view.with_ui('redoc', cache_timeout=0), name='portfolio'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/currency',
                currency_schema_view.with_ui('redoc', cache_timeout=0), name='currency'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/instrument',
                instrument_schema_view.with_ui('redoc', cache_timeout=0), name='instrument'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/transaction',
                transaction_schema_view.with_ui('redoc', cache_timeout=0), name='transaction'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/counterparty',
                counterparty_schema_view.with_ui('redoc', cache_timeout=0), name='counterparty'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/strategy',
                strategy_schema_view.with_ui('redoc', cache_timeout=0), name='strategy'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/report',
                report_schema_view.with_ui('redoc', cache_timeout=0), name='report'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/procedure',
                procedure_schema_view.with_ui('redoc', cache_timeout=0), name='procedure'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/ui',
                ui_schema_view.with_ui('redoc', cache_timeout=0), name='ui'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/explorer',
                explorer_schema_view.with_ui('redoc', cache_timeout=0), name='explorer'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/import',
                import_schema_view.with_ui('redoc', cache_timeout=0), name='import'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/iam',
                iam_schema_view.with_ui('redoc', cache_timeout=0), name='iam'),
        re_path(r'^' + settings.BASE_API_URL + '/docs/api/v1/vault',
                vault_schema_view.with_ui('redoc', cache_timeout=0), name='vault'),

    ]

    return urlpatterns
