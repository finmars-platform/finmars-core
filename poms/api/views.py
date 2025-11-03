import json
import logging
import sys
from datetime import date, datetime, timedelta
from functools import lru_cache

import croniter
import pexpect
import psutil
import pytz
import requests
from babel import Locale
from babel.dates import get_timezone, get_timezone_gmt, get_timezone_name
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone, translation
from django.views.static import serve
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from poms.api.serializers import (
    CalcPeriodDateSerializer,
    EmailSerializer,
    ExpressionSerializer,
    Language,
    LanguageSerializer,
    PickDatesFromRangeSerializer,
    SplitDateRangeSerializer,
    Timezone,
    TimezoneSerializer,
    UtilsDateSerializer,
)
from poms.common.storage import get_storage
from poms.common.utils import (
    calculate_period_date,
    get_closest_bday_of_yesterday,
    get_last_business_day,
    get_list_of_business_days_between_two_dates,
    get_list_of_dates_between_two_dates,
    is_business_day,
    last_day_of_month,
    pick_dates_from_range,
    split_date_range,
)
from poms.common.views import AbstractViewSet
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, PriceHistory, PricingPolicy
from poms.integrations.tasks import send_mail
from poms.schedules.models import ScheduleInstance
from poms.vault.vault import FinmarsVault
from poms.workflows_handler import get_workflows_list

_languages = [Language(code, name) for code, name in settings.LANGUAGES]

_l = logging.getLogger("poms.api")


@lru_cache
def _get_timezones(locale, now):
    locale = Locale(locale)
    timezones = []
    for code in pytz.common_timezones:
        tz = get_timezone(code)
        d = timezone.localtime(now, tz)
        tz_offset = get_timezone_gmt(datetime=d, locale=locale)[3:]
        name = f"{tz_offset} - {get_timezone_name(tz, width='short', locale=locale)}"
        timezones.append(Timezone(code, name, offset=d.utcoffset()))
    timezones = sorted(timezones, key=lambda v: v.offset)
    return timezones


def get_timezones():
    now = timezone.now()
    now = now.replace(minute=0, second=0, microsecond=0)
    return _get_timezones(translation.get_language(), now)


class LanguageViewSet(AbstractViewSet):
    serializer_class = LanguageSerializer

    def list(self, request, *args, **kwargs):
        languages = _languages
        serializer = self.get_serializer(instance=languages, many=True)
        return Response(serializer.data)


class TimezoneViewSet(AbstractViewSet):
    serializer_class = TimezoneSerializer

    def list(self, request, *args, **kwargs):
        timezones = get_timezones()
        serializer = self.get_serializer(instance=timezones, many=True)
        return Response(serializer.data)


class EmailViewSet(AbstractViewSet):
    serializer_class = EmailSerializer

    def list(self, request, *args, **kwargs):
        return Response({"message": "not_implemented"}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            send_mail(**serializer.validated_data)
            return Response({"message": "Email is being sent."}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpressionViewSet(AbstractViewSet):
    serializer_class = ExpressionSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data={"expression": "now()", "is_eval": True})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StatsViewSet(AbstractViewSet):
    def get_first_transaction_date(self):
        from poms.transactions.models import Transaction

        trns = Transaction.objects.all().order_by("accounting_date")

        if len(trns):
            return trns[0].accounting_date

        return None

    def get_general_section(self):
        from poms.accounts.models import Account
        from poms.currencies.models import Currency
        from poms.instruments.models import Instrument
        from poms.portfolios.models import Portfolio
        from poms.transactions.models import ComplexTransaction, Transaction

        result = {
            "total_instruments": Instrument.objects.count(),
            "total_complex_transactions": ComplexTransaction.objects.filter(
                transactions__accounting_date__gte=self.date_from
            ).count(),
            "total_base_transactions": Transaction.objects.filter(accounting_date__gte=self.date_from).count(),
            "total_portfolios": Portfolio.objects.count(),
            "total_accounts": Account.objects.count(),
            "total_currencies": Currency.objects.count(),
            "total_pricing_policies": PricingPolicy.objects.count(),
            "first_transaction_date": self.first_transaction_date,
            "days_from_first_transaction": len(self.days_from_first_transaction),
            "bdays_from_first_transaction": len(self.bdays_from_first_transaction),
        }

        return result

    def get_price_history_section(self, portfolio, portfolio_stats, instruments_ids):
        from poms.instruments.models import Instrument

        total_pricing_policies = PricingPolicy.objects.count()  # noqa: F841

        result = {"filled_items": 0, "items_to_fill": 0}

        pricing_policies = []

        instruments_count = Instrument.objects.filter(id__in=instruments_ids).count()

        for pricing_policy in PricingPolicy.objects.all():
            pricing_policy_result = {
                "expecting_histories": len(self.days_from_first_transaction) * instruments_count,
                "expecting_bdays_histories": len(self.bdays_from_first_transaction) * instruments_count,
                "price_histories": PriceHistory.objects.filter(
                    date__gte=self.date_from,
                    pricing_policy=pricing_policy,
                    instrument_id__in=instruments_ids,
                ).count(),
            }

            try:
                pricing_policy_result["filled_percent"] = round(
                    PriceHistory.objects.filter(
                        date__gte=self.date_from,
                        pricing_policy=pricing_policy,
                        instrument_id__in=instruments_ids,
                    ).count()
                    / (len(self.bdays_from_first_transaction) * instruments_count / 100)
                )
            except Exception:
                pricing_policy_result["filled_percent"] = 0

            pricing_policy_result["pricing_policy"] = {
                "id": pricing_policy.id,
                "name": pricing_policy.name,
                "user_code": pricing_policy.user_code,
            }

            instruments = []

            for instrument in Instrument.objects.filter(id__in=instruments_ids):
                instrument_result = {}

                instrument_result["instrument"] = {
                    "id": instrument.id,
                    "user_code": instrument.user_code,
                    "name": instrument.name,
                }
                instrument_result["expecting_prices"] = len(self.days_from_first_transaction)
                instrument_result["expecting_bdays_prices"] = len(self.bdays_from_first_transaction)
                instrument_result["prices"] = PriceHistory.objects.filter(
                    instrument=instrument,
                    date__gte=self.date_from,
                    pricing_policy=pricing_policy,
                ).count()

                try:
                    instrument_result["last_price_date"] = (
                        PriceHistory.objects.filter(instrument=instrument, date__gte=self.date_from)
                        .order_by("-date")[0]
                        .date
                    )
                except Exception:
                    instrument_result["last_price_date"] = None

                instruments.append(instrument_result)

            pricing_policy_result["instruments"] = instruments

            # Price History stats

            result["filled_items"] = result["filled_items"] + pricing_policy_result["price_histories"]
            result["items_to_fill"] = result["items_to_fill"] + (
                len(self.bdays_from_first_transaction) * instruments_count
            )

            # Portfolio stats

            portfolio_stats["filled_items"] = (
                portfolio_stats["filled_items"] + pricing_policy_result["price_histories"]
            )
            portfolio_stats["items_to_fill"] = portfolio_stats["items_to_fill"] + (
                len(self.bdays_from_first_transaction) * instruments_count
            )

            pricing_policies.append(pricing_policy_result)

        result["pricing_policies"] = pricing_policies
        try:
            result["filled_percent"] = round(result["filled_items"] / (result["items_to_fill"] / 100))
        except Exception:
            result["filled_percent"] = 0

        return result

    def get_currency_history_section(self, portfolio, portfolio_stats, currencies_ids):
        from poms.currencies.models import Currency, CurrencyHistory

        total_pricing_policies = PricingPolicy.objects.count()  # noqa: F841

        result = {"filled_items": 0, "items_to_fill": 0}

        pricing_policies = []

        for pricing_policy in PricingPolicy.objects.all():
            currencies_count = Currency.objects.filter(id__in=currencies_ids).count()

            pricing_policy_result = {
                "expecting_histories": len(self.days_from_first_transaction) * currencies_count,
                "expecting_bdays_histories": len(self.bdays_from_first_transaction) * currencies_count,
                "currency_histories": CurrencyHistory.objects.filter(
                    date__gte=self.date_from,
                    pricing_policy=pricing_policy,
                    currency_id__in=currencies_ids,
                ).count(),
            }

            try:
                pricing_policy_result["filled_percent"] = round(
                    CurrencyHistory.objects.filter(
                        date__gte=self.date_from,
                        pricing_policy=pricing_policy,
                        currency_id__in=currencies_ids,
                    ).count()
                    / (len(self.bdays_from_first_transaction) * currencies_count / 100)
                )
            except Exception:
                pricing_policy_result["filled_percent"] = 0

            pricing_policy_result["pricing_policy"] = {
                "id": pricing_policy.id,
                "name": pricing_policy.name,
                "user_code": pricing_policy.user_code,
            }

            currencies = []

            for currency in Currency.objects.filter(id__in=currencies_ids):
                currency_result = {}

                currency_result["currency"] = {
                    "id": currency.id,
                    "user_code": currency.user_code,
                    "name": currency.name,
                }
                currency_result["expecting_fxrates"] = len(self.days_from_first_transaction)
                currency_result["expecting_bdays_fxrates"] = len(self.bdays_from_first_transaction)
                currency_result["fxrates"] = CurrencyHistory.objects.filter(
                    currency=currency,
                    date__gte=self.date_from,
                    pricing_policy=pricing_policy,
                ).count()

                try:
                    currency_result["last_fxrate_date"] = (
                        CurrencyHistory.objects.filter(currency=currency, date__gte=self.date_from)
                        .order_by("-date")[0]
                        .date
                    )
                except Exception:
                    currency_result["last_fxrate_date"] = None

                currencies.append(currency_result)

            pricing_policy_result["currencies"] = currencies

            # Currency history stat

            result["filled_items"] = result["filled_items"] + pricing_policy_result["currency_histories"]
            result["items_to_fill"] = result["items_to_fill"] + (
                len(self.bdays_from_first_transaction) * currencies_count
            )

            # Portfolio stat

            portfolio_stats["filled_items"] = (
                portfolio_stats["filled_items"] + pricing_policy_result["currency_histories"]
            )
            portfolio_stats["items_to_fill"] = portfolio_stats["items_to_fill"] + (
                len(self.bdays_from_first_transaction) * currencies_count
            )

            pricing_policies.append(pricing_policy_result)

        result["pricing_policies"] = pricing_policies
        try:
            result["filled_percent"] = round(result["filled_items"] / (result["items_to_fill"] / 100))
        except Exception:
            result["filled_percent"] = 0

        return result

    def get_nav_history_section(self, portfolio, portfolio_stats):
        from poms.widgets.models import BalanceReportHistory

        result = {
            "expecting_histories": len(self.days_from_first_transaction),
            "expecting_bdays_histories": len(self.bdays_from_first_transaction),
        }

        result["nav_histories"] = BalanceReportHistory.objects.filter(
            portfolio=portfolio, date__gte=self.date_from
        ).count()

        result["filled_percent"] = round(result["nav_histories"] / (len(self.bdays_from_first_transaction) / 100))

        try:
            result["last_nav_history_date"] = (
                BalanceReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from)
                .order_by("-date")[0]
                .date
            )
        except Exception:
            result["last_nav_history_date"] = None

        portfolio_stats["filled_items"] = portfolio_stats["filled_items"] + result["nav_histories"]
        portfolio_stats["items_to_fill"] = portfolio_stats["items_to_fill"] + (len(self.bdays_from_first_transaction))

        return result

    def get_pl_history_section(self, portfolio, portfolio_stats):
        from poms.widgets.models import PLReportHistory

        result = {
            "expecting_pl_histories": len(self.days_from_first_transaction),
            "expecting_pl_bdays_histories": len(self.bdays_from_first_transaction),
        }

        result["pl_histories"] = PLReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()
        result["filled_percent"] = round(result["pl_histories"] / (len(self.bdays_from_first_transaction) / 100))

        try:
            result["last_pl_history_date"] = (
                PLReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by("-date")[0].date
            )
        except Exception:
            result["last_pl_history_date"] = None

        portfolio_stats["filled_items"] = portfolio_stats["filled_items"] + result["pl_histories"]
        portfolio_stats["items_to_fill"] = portfolio_stats["items_to_fill"] + (len(self.bdays_from_first_transaction))

        return result

    def get_widget_stats_history_section(self, portfolio, portfolio_stats):
        from poms.widgets.models import WidgetStats

        result = {
            "expecting_widget_stats": len(self.days_from_first_transaction),
            "expecting_bdays_widget_stats": len(self.bdays_from_first_transaction),
        }

        result["widget_stats"] = WidgetStats.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()
        result["filled_percent"] = round(result["widget_stats"] / (len(self.bdays_from_first_transaction) / 100))

        try:
            result["last_widget_stats_date"] = (
                WidgetStats.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by("-date")[0].date
            )
        except Exception:
            result["last_widget_stats_date"] = None

        portfolio_stats["filled_items"] = portfolio_stats["filled_items"] + result["widget_stats"]
        portfolio_stats["items_to_fill"] = portfolio_stats["items_to_fill"] + (len(self.bdays_from_first_transaction))

        return result

    def list(self, request, *args, **kwargs):  # noqa: PLR0915
        from poms.transactions.models import ComplexTransaction

        result = {}

        self.period = request.query_params.get("period", "this_year")

        first_transaction_date = self.get_first_transaction_date()
        bday_yesterday = get_closest_bday_of_yesterday()

        self.date_to = bday_yesterday

        if first_transaction_date:
            self.first_transaction_date = self.get_first_transaction_date()

            self.date_from = self.first_transaction_date

            if self.period == "since_inception":
                self.date_from = self.first_transaction_date

            if self.period == "this_year":
                self.date_from = date(date.today().year, 1, 1)

            if self.period == "last_year":
                self.date_from = date(date.today().year - 1, 1, 1)

            self.date_from = max(self.date_from, self.first_transaction_date)

            self.days_from_first_transaction = get_list_of_dates_between_two_dates(self.date_from, self.date_to)
            self.bdays_from_first_transaction = get_list_of_business_days_between_two_dates(
                self.date_from, self.date_to
            )

            from poms.portfolios.models import Portfolio
            from poms.transactions.models import Transaction

            portfolios = []

            for portfolio in Portfolio.objects.all():
                portfolio_item = {}

                portfolio_stats = {"filled_items": 0, "items_to_fill": 0}

                portfolio_item["portfolio"] = {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "user_code": portfolio.user_code,
                }

                portfolio_item["complex_transactions"] = ComplexTransaction.objects.filter(
                    transactions__portfolio=portfolio,
                    transactions__accounting_date__gte=self.date_from,
                ).count()
                portfolio_item["transactions"] = Transaction.objects.filter(
                    portfolio=portfolio, accounting_date__gte=self.date_from
                ).count()

                instruments_ids = list(
                    Transaction.objects.filter(portfolio=portfolio).values_list("instrument", flat=True)
                )
                instruments_ids = instruments_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list("linked_instrument", flat=True)
                )
                instruments_ids = instruments_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list("allocation_balance", flat=True)
                )
                instruments_ids = instruments_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list("allocation_pl", flat=True)
                )

                portfolio_item["related_instruments"] = Instrument.objects.filter(id__in=instruments_ids).count()

                currency_ids = list(
                    Transaction.objects.filter(portfolio=portfolio).values_list("transaction_currency", flat=True)
                )
                currency_ids = currency_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list("settlement_currency", flat=True)
                )

                portfolio_item["related_currencies"] = Currency.objects.filter(id__in=currency_ids).count()

                portfolio_item["price_history"] = self.get_price_history_section(
                    portfolio, portfolio_stats, instruments_ids
                )
                portfolio_item["currency_history"] = self.get_currency_history_section(
                    portfolio, portfolio_stats, currency_ids
                )
                portfolio_item["nav_history"] = self.get_nav_history_section(portfolio, portfolio_stats)
                portfolio_item["pl_history"] = self.get_pl_history_section(portfolio, portfolio_stats)
                portfolio_item["widget_stats_history"] = self.get_widget_stats_history_section(
                    portfolio, portfolio_stats
                )

                portfolio_item["portfolio_stats"] = portfolio_stats
                portfolio_item["filled_percent"] = round(
                    portfolio_item["portfolio_stats"]["filled_items"]
                    / (portfolio_item["portfolio_stats"]["items_to_fill"] / 100)
                )

                trns = Transaction.objects.filter(portfolio=portfolio).order_by("accounting_date")
                portfolio_item["first_transaction_date"] = []
                if len(trns):
                    portfolio_item["first_transaction_date"] = trns[0].accounting_date

                portfolios.append(portfolio_item)

            result["portfolios"] = portfolios
            # important to be after other section to calc overall percent
            result["general"] = self.get_general_section()
            result["date_from"] = self.date_from
            result["date_to"] = self.date_to

            for item in result["portfolios"]:
                items_to_fill = 0
                filled_items = 0

                items_to_fill = items_to_fill + item["portfolio_stats"]["items_to_fill"]
                filled_items = filled_items + item["portfolio_stats"]["filled_items"]

                result["general"]["filled_percent"] = round(filled_items / (items_to_fill / 100))

        else:
            result["error_message"] = "No Transactions"

        return Response(result)


class SystemInfoViewSet(AbstractViewSet):
    def __vm_info(
        self,
    ):
        items = []

        uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())

        items.append(
            {
                "name": "Uptime",
                "user_code": "uptime",
                "values": [{"key": "days", "name": "Days", "value": str(uptime)}],
            }
        )

        memory = psutil.virtual_memory()

        items.append(
            {
                "name": "Memory",
                "user_code": "memory",
                "values": [
                    {
                        "key": "total",
                        "name": "Total (MB)",
                        "value": round(memory.total / 1024 / 1024),
                    },
                    {
                        "key": "used",
                        "name": "Used (MB)",
                        "value": round(memory.used / 1024 / 1024),
                    },
                    {
                        "key": "available",
                        "name": "Available (MB)",
                        "value": round(memory.available / 1024 / 1024),
                    },
                    {"key": "percent", "name": "Percent", "value": memory.percent},
                ],
            }
        )

        disk = psutil.disk_usage("/")

        items.append(
            {
                "name": "Disk",
                "user_code": "disk",
                "values": [
                    {
                        "key": "total",
                        "name": "Total (MB)",
                        "value": round(disk.total / 1024 / 1024),
                    },
                    {
                        "key": "used",
                        "name": "Used (MB)",
                        "value": round(disk.used / 1024 / 1024),
                    },
                    {
                        "key": "free",
                        "name": "Free (MB)",
                        "value": round(disk.free / 1024 / 1024),
                    },
                    {"key": "percent", "name": "Percent", "value": disk.percent},
                ],
            }
        )

        shell_cmd = "ps aux | grep [b]ackend"
        c = pexpect.spawn("/bin/bash", ["-c", shell_cmd])
        pexpect_result = c.read()

        celery_worker_state = True

        if not pexpect_result:
            celery_worker_state = False

        items.append(
            {
                "name": "Celery Worker",
                "user_code": "celery_worker",
                "values": [
                    {"key": "active", "name": "Active", "value": celery_worker_state},
                ],
            }
        )

        shell_cmd = "ps aux | grep [d]jango_celery_beat"
        c = pexpect.spawn("/bin/bash", ["-c", shell_cmd])
        pexpect_result = c.read()

        celery_beat_state = True

        if not pexpect_result:
            celery_beat_state = False

        items.append(
            {
                "name": "Celery Beat",
                "user_code": "celery_beat",
                "values": [
                    {"key": "active", "name": "Active", "value": celery_beat_state},
                ],
            }
        )

        _l.info("pexpect_result read %s", pexpect_result)

        return items

    def __python_version(
        self,
    ):
        return sys.version

    def __pip_freeze_info(self):
        if not getattr(self, "pip_freeze_data", None):
            self.pip_freeze_data = {"all": {}, "django": "-"}

            c = pexpect.spawn("/bin/bash", ["-c", "pip3 freeze"])

            for freeze_item in c.readlines():
                if freeze_item:
                    lib_item = freeze_item.decode().strip()
                    lib_item_splited = lib_item.split("==")
                    if len(lib_item_splited) > 1:
                        self.pip_freeze_data["all"][lib_item_splited[0]] = lib_item_splited[1]

                        if lib_item_splited[0] == "Django":
                            self.pip_freeze_data["django"] = lib_item_splited[1]

        return self.pip_freeze_data

    def __db_version(
        self,
    ):
        db_version = "unknown"

        db_vendor_to_query_version = {
            "postgresql": "SELECT version();",
            "sqlite": "SELECT sqlite_version();",
            "mysql": "SELECT VERSION();",
            "oracle": "SELECT * FROM v$version;",
        }

        if connection.vendor in db_vendor_to_query_version:
            with connection.cursor() as cursor:
                cursor.execute(db_vendor_to_query_version[connection.vendor])
                db_row = cursor.fetchone()
                if db_row:
                    db_version = db_row

        return db_version

    def __db_adapter_info(
        self,
    ):
        try:
            db_adapter_info = {
                "settings_engine": settings.DATABASES["default"]["ENGINE"],
                "adapter_vendor": connection.vendor,
                "adapter": connection.Database.__name__,
                "adapter_version": connection.Database.__version__,
                "db_version": self.__db_version(),
            }
        except Exception as e:
            _l.error("Could not get db_adapter_info %s", e)
            db_adapter_info = {"adapter_status": "unknown"}

        return db_adapter_info

    def __storage_adapter_info(
        self,
    ):
        try:
            storage = get_storage()
            storage_adapter_info = {
                "adapter_name": storage.__class__.__name__,
                #'adapter_version': storage.__class__.__version__
            }
        except Exception as e:
            _l.error("Could not get storage_adapter_info %s", e)
            storage_adapter_info = {"adapter_name": "unknown"}

        return storage_adapter_info

    def __celery_info(
        self,
    ):
        from celery import current_app

        # pprint(current_app.conf['task_routes'])
        try:
            i = current_app.control.inspect()
            celery_info = {
                # Получить информацию о зарегистрированных задачах
                "registered_tasks": i.registered_tasks(),
                # Получить информацию о запущенных задачах
                "active_tasks": i.active(),
                # Получить информацию о запланированных задачах
                "scheduled_tasks": i.scheduled(),
                # Получить информацию о зарезервированных задачах
                "reserved_tasks": i.reserved(),
                # Получить информацию о работающих воркерах
                "stats": i.stats(),
            }
        except Exception as e:
            _l.error("Could not get celery_info %s", e)
            celery_info = {"status": "unhealth"}

        return celery_info

    def __rabbitmq_status(
        self,
    ):
        from celery import current_app

        # pprint(current_app.conf['task_routes'])
        try:
            conn = current_app.connection()
            transport = conn.transport
            mq_conn = transport.establish_connection()
            # pprint(dir(mq_conn))

            rabbitmq_status = {
                "default_connection_params": transport.default_connection_params,
                "driver_name": transport.driver_name,
                "driver_version": transport.driver_version(),
                #'connection': transport.establish_connection(),
                "server_properties": mq_conn.server_properties,
                #'heartbeat_check': transport.heartbeat_check(conn),
                #'verify_connection': transport.verify_connection(conn)
            }
            mq_conn.close()
        except Exception as e:
            _l.error("Could not get rabbitmq info %s", e)
            rabbitmq_status = {"status": "unhealth"}

        return rabbitmq_status

    def __workflow_status(self, request, *args, **kwargs):
        base_url = ""

        if request.realm_code:
            base_url = request.realm_code + "/" + request.space_code
        else:
            base_url = request.space_code

        workflow_url = "https://" + settings.DOMAIN_NAME + "/" + base_url + "/workflow/api/workflow/"
        workflow_status = "unhealty"

        try:
            req = requests.get(workflow_url)
            if req.status_code == 200:
                workflow_status = "healty"
        except Exception:
            workflow_status = "unhealty"

        return {"workflow_url": workflow_url, "workflow_status": workflow_status}

    def __redis_status(self):
        status = "unhealty"

        try:
            cache.set("check_healty_status", 1, 10)

            if cache.get("check_healty_status", 0) == 1:
                status = "healty"

        except Exception:
            status = "unhealty"

        return {
            "status": status,
        }

    def __vault_status(self, request, *args, **kwargs):
        try:
            finmars_vault = FinmarsVault(realm_code=request.realm_code, space_code=request.space_code)
            # it seems that this function, in case something is wrong with the Vault, always gives an exeption
            finmars_vault.get_health()
            status = "health"
        except Exception:
            status = "unhealth"

        return {"status": status}

    def list(self, request, *args, **kwargs):
        result = {}

        result["results"] = {
            "vm": self.__vm_info(),
            "python_version": self.__python_version(),
            "django_version": self.__pip_freeze_info()["django"],
            "pip_freeze": self.__pip_freeze_info()["all"],
            "db_adapter": self.__db_adapter_info(),
            "storage_adapter": self.__storage_adapter_info(),
            "vault_status": self.__vault_status(request),
            "celery_status": self.__celery_info(),
            "workflow_status": self.__workflow_status(request),
            "rabbitmq_status": self.__rabbitmq_status(),
            "redis_status": self.__redis_status(),
        }

        return Response(result)


class SystemLogsViewSet(AbstractViewSet):
    def list(self, request, *args, **kwargs):
        result = {}

        shell_cmd = "ls -la /var/log/finmars/backend/  | awk '{print $9}'"
        c = pexpect.spawn("/bin/bash", ["-c", shell_cmd])
        pexpect_result = c.read().decode("utf-8")

        # items = pexpect_result.split('\')

        lines = pexpect_result.splitlines()

        items = []
        for line in lines:
            if line not in ["", ".", ".."]:
                items.append(line)

        _l.info("SystemInfoLogsViewSet.items %s", items)

        result["results"] = items

        return Response(result)

    @action(detail=False, methods=["get"], url_path="view-log")
    def view_log(self, request, realm_code=None, space_code=None):
        log_file = request.query_params.get("log_file", "django.log")

        log_file = "/var/log/finmars/backend/" + log_file

        file = open(log_file)  # noqa SIM115

        return HttpResponse(file, content_type="plain/text")


class TablesSizeViewSet(AbstractViewSet):
    @staticmethod
    def dictfetchall(cursor):
        """
        Returns a list of dicts representing the rows in the given database cursor.
        Each dictionary represents a row in the result set, with keys corresponding
        to the column names and values corresponding to the column values.
        Parameters:
        cursor (database cursor): The database cursor to fetch results from.
        Returns:
        list[dict]: A list of dictionaries representing the rows in the result set.
        """
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

    def list(self, request, *args, **kwargs):
        result = {"results": []}

        query = f"""
            select
              table_name,
              pg_size_pretty(pg_total_relation_size(quote_ident(table_name))),
              pg_total_relation_size(quote_ident(table_name))
            from information_schema.tables
            where table_schema = '{request.space_code}'
            order by 3 desc;
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            result["results"] = self.dictfetchall(cursor)

        return Response(result)

    @action(detail=False, methods=["get"], url_path="view-log")
    def view_log(self, request, realm_code=None, space_code=None):
        log_file = request.query_params.get("log_file", "django.log")

        log_file = f"/var/log/finmars/backend/{log_file}"

        file = open(log_file)  # noqa SIM115

        return HttpResponse(file, content_type="plain/text")


class RecycleBinViewSet(AbstractViewSet, ModelViewSet):
    def get_queryset(self):
        from poms.transactions.models import ComplexTransaction

        return ComplexTransaction.objects.filter(is_deleted=True)

    def get_serializer_class(self):
        from poms.transactions.serializers import ComplexTransactionDeleteSerializer

        return ComplexTransactionDeleteSerializer

    def list(self, request, *args, **kwargs):
        from poms.transactions.models import ComplexTransaction

        date_from = request.query_params.get("date_from", None)
        date_to = request.query_params.get("date_to", None)
        query = request.query_params.get("query", None)

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        else:
            date_to = timezone.now()

        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        else:
            date_from = date_to - timedelta(days=7)

        if date_from >= date_to:
            date_from = date_to - timedelta(days=7)

        qs = ComplexTransaction.objects.filter(is_deleted=True, modified_at__gte=date_from, modified_at__lte=date_to)

        if query:
            pieces = query.split(" ")

            text_q = Q()
            user_text_1_q = Q()
            user_text_2_q = Q()
            user_text_3_q = Q()
            user_text_4_q = Q()
            user_text_5_q = Q()

            for piece in pieces:
                text_q.add(Q(text__icontains=piece), Q.AND)
                user_text_1_q.add(Q(user_text_1__icontains=piece), Q.AND)
                user_text_2_q.add(Q(user_text_2__icontains=piece), Q.AND)
                user_text_3_q.add(Q(user_text_3__icontains=piece), Q.AND)
                user_text_4_q.add(Q(user_text_4__icontains=piece), Q.AND)
                user_text_5_q.add(Q(user_text_5__icontains=piece), Q.AND)

            options = Q()

            options.add(text_q, Q.OR)
            options.add(user_text_1_q, Q.OR)
            options.add(user_text_2_q, Q.OR)
            options.add(user_text_3_q, Q.OR)
            options.add(user_text_4_q, Q.OR)
            options.add(user_text_5_q, Q.OR)
            options.add(Q(transaction_unique_code__icontains=query), Q.OR)
            options.add(Q(deleted_transaction_unique_code__icontains=query), Q.OR)
            options.add(Q(code__icontains=query), Q.OR)

            qs = qs.filter(options)

        page = self.paginate_queryset(qs)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="clear-bin")
    def clear_bin(self, request, realm_code=None, space_code=None):
        date_from = request.data.get("date_from", None)
        date_to = request.data.get("date_to", None)

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)

        from django.contrib.contenttypes.models import ContentType

        from poms.transactions.models import ComplexTransaction

        ids = ComplexTransaction.objects.filter(
            is_deleted=True, modified_at__gte=date_from, modified_at__lte=date_to
        ).values_list("id", flat=True)

        content_type = ContentType.objects.get(app_label="transactions", model="complextransaction")
        content_type_key = content_type.app_label + "." + content_type.model

        options_object = {"content_type": content_type_key, "ids": list(ids)}

        from poms.celery_tasks.models import CeleryTask

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            options_object=options_object,
            verbose_name="Bulk Delete",
            type="bulk_delete",
        )

        from poms_app import celery_app

        celery_app.send_task(
            "celery_tasks.bulk_delete",
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "realm_code": celery_task.master_user.realm_code,
                    "space_code": celery_task.master_user.space_code,
                },
            },
            queue="backend-background-queue",
        )

        return Response({"task_id": celery_task.id})


class UniversalInputViewSet(AbstractViewSet):
    def create(self, request):
        if request.content_type == "application/json":
            data = request.data
        else:
            try:
                data = json.loads(request.data)
            except json.JSONDecodeError:
                return Response(status=400, data={"error": "Invalid data format"})

        from poms.celery_tasks.models import CeleryTask

        celery_task = CeleryTask.objects.create(
            member=self.request.user.member,
            master_user=self.request.user.master_user,
            options_object=data,
            type="universal_input",
        )

        from poms.celery_tasks.tasks import universal_input

        universal_input.apply_async(
            kwargs={
                "task_id": celery_task.id,
                "context": {
                    "space_code": celery_task.master_user.space_code,
                    "realm_code": celery_task.master_user.realm_code,
                },
            }
        )

        # _l.info('UniversalInputViewSet.data %s' % data)

        return Response({"status": "ok", "task_id": celery_task.id})


class CalendarEventsViewSet(AbstractViewSet):
    def list(self, request, *args, **kwargs):  # noqa: PLR0912, PLR0915
        """
        Method to create Events list for Finmars Web Interface Calendar Page
        It is aggregates Celery Tasks, Data Procedures, Pricing Procedures, Schedules
        and Workflows in future
        :param request:
        :param args:
        :param kwargs:
        :return:
        """

        from poms.celery_tasks.models import CeleryTask
        from poms.procedures.models import (
            BaseProcedureInstance,
            PricingProcedureInstance,
            RequestDataFileProcedureInstance,
        )
        from poms.schedules.models import Schedule

        def cronexp(field):
            """Representation of cron expression."""
            return field and str(field).replace(" ", "") or "*"

        date_from = request.query_params.get("date_from", None)
        date_to = request.query_params.get("date_to", None)
        filter = request.query_params.get("filter", None)

        if not date_from:
            date_from = datetime.today().replace(day=1)
        else:
            date_from = datetime.strptime(date_from, "%Y-%m-%d").date()

        if not date_to:
            date_to = last_day_of_month(date_from)
        else:
            date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

        if not filter:
            filter = [
                "data_procedure",
                "expression_procedure",
                "pricing_procedure",
                "celery_task",
            ]
        else:
            filter = filter.split(",")

        _l.info("date_from %s", date_from)
        _l.info("date_to %s", date_to)

        dates = get_list_of_dates_between_two_dates(date_from, date_to)  # noqa: F841

        results = []
        # Format for Date Calendar
        # {
        #     title  : 'event2',
        #     start  : '2010-01-05',
        #     end    : '2010-01-07'
        # },

        # Collect User Schedules

        if "schedule" in filter:
            schedules = Schedule.objects.all()

            for schedule in schedules:
                cron = croniter.croniter(schedule.cron_expr, date_from)

                lookup = True
                while lookup:
                    nextdate = cron.get_next(datetime)

                    item = {
                        "title": schedule.name,
                        "start": str(nextdate),
                        "classNames": ["user"],
                        "backgroundColor": "lightgrey",
                        "extendedProps": {
                            "type": "schedule",
                        },
                    }

                    results.append(item)

                    if nextdate > date_to:
                        lookup = False

        # Schedule Instance

        if "schedule_instance" in filter:
            schedule_instances = ScheduleInstance.objects.filter(created_at__gte=date_from, created_at__lte=date_to)
            for instance in schedule_instances:
                item = {
                    "start": instance.created_at,
                    "classNames": ["user"],
                    "extendedProps": {
                        "type": "schedule_instance",
                        "id": instance.id,
                        "payload": {
                            "schedule": instance.schedule_id,
                            "schedule_object": {
                                "id": instance.schedule.id,
                                "user_code": instance.schedule.user_code,
                            },
                            "status": instance.status,
                            "current": instance.current_processing_procedure_number,
                            "total": len(instance.schedule.procedures.all()),
                        },
                    },
                }

                item["backgroundColor"] = "green"

                if instance.status == BaseProcedureInstance.STATUS_ERROR:
                    item["backgroundColor"] = "red"

                if instance.status == BaseProcedureInstance.STATUS_PENDING:
                    item["backgroundColor"] = "blue"

                item["title"] = f"Schedule {instance.schedule.user_code}"

                results.append(item)

        # Data Procedures

        if "data_procedure" in filter:
            data_procedure_instances = RequestDataFileProcedureInstance.objects.filter(
                created_at__gte=date_from, created_at__lte=date_to
            )
            for instance in data_procedure_instances:
                item = {
                    "start": instance.created_at,
                    "classNames": ["user"],
                    "extendedProps": {
                        "type": "data_procedure",
                        "id": instance.id,
                        "payload": {
                            "action": instance.action,
                            "provider": instance.provider,
                            "status": instance.status,
                            "error_message": instance.error_message,
                        },
                    },
                }

                item["backgroundColor"] = "green"

                if instance.status == BaseProcedureInstance.STATUS_ERROR:
                    item["backgroundColor"] = "red"

                if instance.status == BaseProcedureInstance.STATUS_PENDING:
                    item["backgroundColor"] = "blue"

                if instance.action_verbose:
                    if instance.provider_verbose:
                        title = instance.provider_verbose + ": " + instance.action_verbose
                    else:
                        title = instance.action_verbose
                else:
                    title = ""

                    if instance.action:
                        title = title + " " + instance.action

                if instance.member:
                    title = title + " by " + instance.member.username

                title = title + " [" + str(instance.id) + "]"

                item["title"] = title

                results.append(item)

        # Pricing Procedures

        if "pricing_procedure" in filter:
            pricing_procedure_instances = PricingProcedureInstance.objects.filter(
                created_at__gte=date_from, created_at__lte=date_to
            )

            for instance in pricing_procedure_instances:
                item = {
                    "start": instance.created_at,
                    "classNames": ["user"],
                    "extendedProps": {
                        "type": "pricing_procedure",
                        "id": instance.id,
                        "payload": {
                            "action": instance.action,
                            "provider": instance.provider,
                            "status": instance.status,
                            "error_message": instance.error_message,
                        },
                    },
                }

                item["backgroundColor"] = "green"

                if instance.status == BaseProcedureInstance.STATUS_ERROR:
                    item["backgroundColor"] = "red"

                if instance.status == BaseProcedureInstance.STATUS_PENDING:
                    item["backgroundColor"] = "blue"

                if instance.action_verbose:
                    if instance.provider_verbose:
                        title = instance.provider_verbose + ": " + instance.action_verbose
                    else:
                        title = instance.action_verbose
                else:
                    title = ""

                    if instance.action:
                        title = title + " " + instance.action

                if instance.member:
                    title = title + " by " + instance.member.username

                title = title + " [" + str(instance.id) + "]"

                item["title"] = title

                results.append(item)

        # Collect Celery Tasks

        if "celery_task" in filter:
            tasks = CeleryTask.objects.filter(created_at__gte=date_from, created_at__lte=date_to)

            for task in tasks:
                item = {
                    "start": task.created_at,
                    "finished_at": task.finished_at,
                    "classNames": ["user"],
                    "extendedProps": {
                        "type": "celery_task",
                        "id": task.id,
                        "payload": {
                            "type": task.type,
                            "status": task.status,
                            "error_message": task.error_message,
                        },
                    },
                }

                item["backgroundColor"] = "green"

                if task.status == CeleryTask.STATUS_ERROR:
                    item["backgroundColor"] = "red"

                if task.status == CeleryTask.STATUS_PENDING:
                    item["backgroundColor"] = "blue"

                if task.verbose_name:
                    title = task.verbose_name
                else:
                    title = ""

                    if task.type:
                        title = title + " " + task.type

                if task.member:
                    title = title + " by " + task.member.username

                title = title + " [" + str(task.id) + "]"

                item["title"] = title

                results.append(item)

        if "workflow" in filter:
            try:
                workflows = get_workflows_list(date_from, date_to, request.realm_code, request.space_code)

                for workflow in workflows:
                    item = {
                        "start": workflow["created"],
                        # 'finished_at': workflow['finished_at'],
                        "classNames": ["user"],
                        "extendedProps": {
                            "type": "workflow",
                            "id": workflow["id"],
                            "payload": {
                                "status": workflow["status"],
                                "payload": workflow["payload"],
                            },
                        },
                    }

                    if workflow["status"] == "error":
                        item["backgroundColor"] = "red"

                    if workflow["status"] == "pending":
                        item["backgroundColor"] = "blue"

                    if workflow["status"] == "success":
                        item["backgroundColor"] = "green"

                    title = workflow["project"] + "." + workflow["user_code"]
                    title = title + " [" + str(workflow["id"]) + "]"

                    item["title"] = title

                    results.append(item)

            except Exception as e:
                _l.error("Could not fetch workflows %s", e)

        response = {}

        response["results"] = results

        return Response(response)


def serve_docs(request, path, **kwargs):
    kwargs["document_root"] = settings.DOCS_ROOT

    return serve(request, path, **kwargs)


class SplitDateRangeViewSet(AbstractViewSet):
    serializer_class = SplitDateRangeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        frequency = serializer.validated_data["frequency"]
        is_only_bday = serializer.validated_data["is_only_bday"]
        dates = split_date_range(start_date, end_date, frequency, is_only_bday)

        return Response({"result": dates}, status=status.HTTP_200_OK)


class CalcPeriodDateViewSet(AbstractViewSet):
    serializer_class = CalcPeriodDateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_date = serializer.validated_data["date"]
        frequency = serializer.validated_data["frequency"]
        shift = serializer.validated_data["shift"]
        is_only_bday = serializer.validated_data["is_only_bday"]
        start = serializer.validated_data["start"]
        dates = calculate_period_date(input_date, frequency, shift, is_only_bday, start)

        return Response({"result": dates}, status=status.HTTP_200_OK)


class PickDatesFromRangeViewSet(AbstractViewSet):
    serializer_class = PickDatesFromRangeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]
        frequency = serializer.validated_data["frequency"]
        is_only_bday = serializer.validated_data["is_only_bday"]
        start = serializer.validated_data["start"]
        dates = pick_dates_from_range(start_date, end_date, frequency, is_only_bday, start)

        return Response({"result": dates}, status=status.HTTP_200_OK)


class LastBusinessDayViewSet(AbstractViewSet):
    serializer_class = UtilsDateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        input_date = serializer.validated_data["date"]
        input_date = get_last_business_day(input_date, True)

        return Response({"result": input_date}, status=status.HTTP_200_OK)


class IsBusinessDayViewSet(AbstractViewSet):
    serializer_class = UtilsDateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        input_date = serializer.validated_data["date"]

        return Response({"result": is_business_day(input_date)}, status=status.HTTP_200_OK)


class LastDayOfMonthViewSet(AbstractViewSet):
    serializer_class = UtilsDateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        input_date = serializer.validated_data["date"]
        input_date = last_day_of_month(input_date)

        return Response({"result": input_date}, status=status.HTTP_200_OK)
