import copy
from unittest import skip

from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.configuration.utils import get_default_configuration_code
from poms.transactions.models import (
    ComplexTransaction,
    ComplexTransactionStatus,
    TransactionType,
    TransactionTypeGroup,
    TransactionTypeInput,
    TransactionTypeInputSettings,
)
from poms.transactions.tests.transaction_type_dicts import (
    RECALCULATE_PAYLOAD,
)

DATE_FORMAT = "%Y-%m-%d"


class TransactionTypeViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/transactions/transaction-type/"
        self.user_code = "developing"
        self.configuration_code = get_default_configuration_code()

    @staticmethod
    def get_transaction_type_group() -> TransactionTypeGroup:
        return TransactionTypeGroup.objects.get(user_code__contains="unified")

    def create_transaction_type(self) -> TransactionType:
        transaction_type_group = self.get_transaction_type_group()
        self.transaction_type = TransactionType.objects.create(
            master_user=self.master_user,
            owner=self.member,
            configuration_code=self.configuration_code,
            user_code=self.user_code,
            name=self.random_string(),
            short_name=self.random_string(3),
            group=transaction_type_group.user_code,
            type=TransactionType.TYPE_DEFAULT,
            user_text_1=self.random_string(),
            user_text_2=self.random_string(),
            user_number_1=str(self.random_int()),
            user_number_2=str(self.random_int()),
            user_date_1=self.random_future_date().strftime(DATE_FORMAT),
            user_date_2=self.random_future_date().strftime(DATE_FORMAT),
            is_deleted=False,
        )
        self.transaction_type.attributes.add(self.create_attribute())
        self.transaction_type.book_transaction_layout = {"test": "test"}
        self.transaction_type.save()
        return self.transaction_type

    def create_transaction_type_settings(self):
        return TransactionTypeInputSettings.objects.create(
            linked_inputs_names=self.random_string(),
            recalc_on_change_linked_inputs=self.random_string(),
        )

    def create_transaction_type_input(self, transaction_type) -> TransactionTypeInput:
        return TransactionTypeInput.objects.create(
            transaction_type=transaction_type,
            name=self.random_string(),
            tooltip=self.random_string(),
            verbose_name=self.random_string(100),
            reference_table=self.random_string(),
            value_type=TransactionTypeInput.NUMBER,
            value=self.random_int(),
            settings=self.create_transaction_type_settings(),
        )

    @staticmethod
    def get_complex_transaction_status(model_id=ComplexTransaction.PENDING):
        return ComplexTransactionStatus.objects.get(id=model_id)

    def create_complex_transaction(self, transaction_type) -> ComplexTransaction:
        transaction = ComplexTransaction.objects.create(
            # mandatory fields
            master_user=self.master_user,
            transaction_type=transaction_type,
            date=self.random_future_date(),
            status=self.get_complex_transaction_status(),
            code=self.random_int(),
            transaction_unique_code=str(self.random_int(1000000, 10000000)),
            # optional fields
            user_text_1=self.random_string(),
            user_text_2=self.random_string(),
            user_number_1=str(self.random_int()),
            user_number_2=str(self.random_int()),
            user_date_1=str(self.random_future_date()),
            user_date_2=str(self.random_future_date()),
        )
        transaction.attributes.add(self.create_attribute())
        transaction.save()

        return transaction

    def prepare_create_data(self) -> dict:
        transaction_type_group = self.get_transaction_type_group()
        return {
            "group": transaction_type_group.user_code,
            "configuration_code": self.random_string(),
            "user_code": self.random_string(7),
            "name": self.random_string(),
            "short_name": self.random_string(3),
            "user_text_1": self.random_string(),
            "user_number_1": str(self.random_int()),
            "user_date_1": self.random_future_date().strftime(DATE_FORMAT),
        }

    def prepare_context_data(self) -> dict:
        instrument = self.create_instrument()
        return {
            "context_instrument": instrument.id,
            "context_pricing_currency": instrument.pricing_currency.id,
            "context_accrued_currency": instrument.accrued_currency.id,
            "context_currency": instrument.pricing_currency.id,
            "context_portfolio": 1,
            "context_account": 1,
            "context_pricing_policy": 1,
            "context_effective_date": self.today(),
            "context_report_date": self.random_future_date(),
            "context_report_start_date": self.today(),
        }

    def test__check_get_api_url(self):
        tt = self.create_transaction_type()
        response = self.client.get(path=f"{self.url}{tt.id}/recalculate/")
        self.assertEqual(response.status_code, 405, response.content)

    @BaseTestCase.cases(
        ("recalculate_inputs", "recalculate_inputs"),
        ("process_mode", "process_mode"),
    )
    def test__check_no_mandatory_param(self, param):
        tt = self.create_transaction_type()
        payload = copy.deepcopy(RECALCULATE_PAYLOAD)
        payload.pop(param)
        response = self.client.put(
            path=f"{self.url}{tt.id}/recalculate/",
            format="json",
            data=payload,
        )
        self.assertEqual(response.status_code, 400, response.content)

    @BaseTestCase.cases(
        ("recalculate_inputs", "recalculate_inputs"),
        ("process_mode", "process_mode"),
    )
    def test__check_empty_param(self, param):
        tt = self.create_transaction_type()
        payload = copy.deepcopy(RECALCULATE_PAYLOAD)
        payload[param] = None
        response = self.client.put(
            path=f"{self.url}{tt.id}/recalculate/",
            format="json",
            data=payload,
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test__check_wrong_process(self):
        tt = self.create_transaction_type()
        payload = copy.deepcopy(RECALCULATE_PAYLOAD)
        payload["process_mode"] = self.random_string()
        response = self.client.put(
            path=f"{self.url}{tt.id}/recalculate/",
            format="json",
            data=payload,
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test__check_wrong_pk(self):
        payload = copy.deepcopy(RECALCULATE_PAYLOAD)
        response = self.client.put(
            path=f"{self.url}{self.random_int()}/recalculate/",
            format="json",
            data=payload,
        )
        self.assertEqual(response.status_code, 404, response.content)

    @skip("need to create transaction type inputs")
    def test__recalculate(self):
        tt = self.create_transaction_type()

        payload = copy.deepcopy(RECALCULATE_PAYLOAD)

        response = self.client.put(
            path=f"{self.url}{tt.id}/recalculate/",
            format="json",
            data=payload,
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
