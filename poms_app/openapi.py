from django.conf import settings
from django.shortcuts import render
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions


# -----------------------------------------
# CUSTOM GENERATOR
# -----------------------------------------
class TenantSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        swagger = super().get_schema(request, public)

        # Replace placeholder parameters with default values
        # (realm_code, space_code) in each path
        for path in list(swagger.paths.keys()):
            new_path = path.replace("{realm_code}", request.realm_code).replace(
                "{space_code}", request.space_code
            )
            swagger.paths[new_path] = swagger.paths[path]
            del swagger.paths[path]

        swagger.security_definitions = {
            "Bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Enter token in format `Bearer <token>`. Token can be generated in /api/v1/auth-tokens/personal-access-token/create-token/",
            },
            "SingleSignOn": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Enter Access Token from Keycloak as `Token <token>`. ",
            },
        }

        # Apply both authentication methods to **all** API endpoints
        swagger.security = [
            {"Bearer": []},  # Allow Bearer token authentication
            {"SingleSignOn": []},  # Allow SingleSignOn token authentication
        ]

        return swagger

    def get_tags(self, operation_keys=None):

        print(f"work? tags {operation_keys}")

        return []


def scheme_get_method_decorator(func):
    """
    This decorator modifies how the get() method works so that
    realm_code and space_code are recognized.
    """

    def wrapper(self, request, version="", format=None, *args, **kwargs):
        return func(self, request, version="", format=None)

    return wrapper


# -----------------------------------------
# BASE FUNCTION TO GENERATE SCHEMA VIEW
# -----------------------------------------
def generate_schema(local_urlpatterns):
    schema_view = get_schema_view(
        openapi.Info(
            title="Finmars API",
            default_version="v1",
            description="Finmars Documentation",
            terms_of_service="https://www.finmars.com/policies/terms/",
            contact=openapi.Contact(email="admin@finmars.com"),
            license=openapi.License(name="BSD License"),
            x_logo={
                "url": "https://finmars.com/wp-content/uploads/2023/04/logo.png",
                "backgroundColor": "#000",
                "href": f"/{settings.REALM_CODE}/docs/api/v1/",
            },
        ),
        patterns=local_urlpatterns,
        public=True,
        permission_classes=[permissions.AllowAny],
        generator_class=TenantSchemaGenerator,
    )

    # Patch the schema_view get() method to handle realm_code/space_code
    schema_view.get = scheme_get_method_decorator(schema_view.get)

    return schema_view


# -----------------------------------------
# PARTIAL DOCUMENTATION FUNCTIONS
# -----------------------------------------
def get_account_documentation(*args, **kwargs):
    import poms.accounts.urls as account_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/accounts/",
            include(account_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_portfolio_documentation(*args, **kwargs):
    import poms.portfolios.urls as portfolio_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/portfolios/",
            include(portfolio_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_currency_documentation(*args, **kwargs):
    import poms.currencies.urls as currency_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/currencies/",
            include(currency_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_instrument_documentation(*args, **kwargs):
    import poms.instruments.urls as instrument_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/instruments/",
            include(instrument_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_transaction_documentation(*args, **kwargs):
    import poms.transactions.urls as transaction_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/transactions/",
            include(transaction_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_counterparty_documentation(*args, **kwargs):
    import poms.counterparties.urls as counterparty_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/counterparties/",
            include(counterparty_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_strategy_documentation(*args, **kwargs):
    import poms.strategies.urls as strategy_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/strategies/",
            include(strategy_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_report_documentation(*args, **kwargs):
    import poms.reports.urls as report_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/reports/",
            include(report_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_procedure_documentation(*args, **kwargs):
    import poms.procedures.urls as procedure_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/procedures/",
            include(procedure_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_ui_documentation(*args, **kwargs):
    import poms.ui.urls as ui_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/ui/",
            include(ui_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_explorer_documentation(*args, **kwargs):
    import poms.explorer.urls as explorer_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/explorer/",
            include(explorer_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_import_documentation(*args, **kwargs):
    import poms.csv_import.urls as csv_import_router
    import poms.integrations.urls as integrations_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/import/",
            include(integrations_router.router.urls),
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/import/",
            include(csv_import_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_iam_documentation(*args, **kwargs):
    import poms.iam.urls as iam_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/iam/",
            include(iam_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_vault_documentation(*args, **kwargs):
    import poms.vault.urls as vault_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/vault/",
            include(vault_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


def get_schedule_documentation(*args, **kwargs):
    import poms.schedules.urls as schedule_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/schedule/",
            include(schedule_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)

def get_celery_tasks_documentation(*args, **kwargs):
    import poms.celery_tasks.urls as celery_router

    local_urlpatterns = [
        path(
            "<slug:realm_code>/<slug:space_code>/api/v1/celery_tasks/",
            include(celery_router.router.urls),
        ),
    ]
    return generate_schema(local_urlpatterns)


# -----------------------------------------
# MAIN PAGE RENDER FUNCTION
# -----------------------------------------
def render_main_page(request, *args, **kwargs):
    context = {"realm_code": request.realm_code, "space_code": request.space_code}
    return render(request, "finmars_redoc.html", context)


# -----------------------------------------
# EXISTING: GET REDOC URL PATTERNS
# -----------------------------------------
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
    schedule_schema_view = get_schedule_documentation()
    celery_tasks_schema_view = get_celery_tasks_documentation()

    return [
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/",
            render_main_page,
            name="main",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/account",
            account_schema_view.with_ui("redoc", cache_timeout=0),
            name="account",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/portfolio",
            portfolio_schema_view.with_ui("redoc", cache_timeout=0),
            name="portfolio",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/currency",
            currency_schema_view.with_ui("redoc", cache_timeout=0),
            name="currency",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/instrument",
            instrument_schema_view.with_ui("redoc", cache_timeout=0),
            name="instrument",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/transaction",
            transaction_schema_view.with_ui("redoc", cache_timeout=0),
            name="transaction",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/counterparty",
            counterparty_schema_view.with_ui("redoc", cache_timeout=0),
            name="counterparty",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/strategy",
            strategy_schema_view.with_ui("redoc", cache_timeout=0),
            name="strategy",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/report",
            report_schema_view.with_ui("redoc", cache_timeout=0),
            name="report",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/procedure",
            procedure_schema_view.with_ui("redoc", cache_timeout=0),
            name="procedure",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/ui",
            ui_schema_view.with_ui("redoc", cache_timeout=0),
            name="ui",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/explorer",
            explorer_schema_view.with_ui("redoc", cache_timeout=0),
            name="explorer",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/import",
            import_schema_view.with_ui("redoc", cache_timeout=0),
            name="import",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/iam",
            iam_schema_view.with_ui("redoc", cache_timeout=0),
            name="iam",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/vault",
            vault_schema_view.with_ui("redoc", cache_timeout=0),
            name="vault",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/schedule",
            schedule_schema_view.with_ui("redoc", cache_timeout=0),
            name="schedule",
        ),
        path(
            "<slug:realm_code>/<slug:space_code>/docs/api/v1/celery_tasks",
            celery_tasks_schema_view.with_ui("redoc", cache_timeout=0),
            name="celery_tasks",
        ),
    ]
