from urllib import parse
from unittest import skip

from django.conf import settings
from django.test import override_settings

from poms.common.common_base_test import BaseTestCase
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import (
    TransactionType,
    TransactionTypeGroup,
    TransactionTypeInput,
    TransactionTypeInputSettings,
    ComplexTransaction,
    ComplexTransactionStatus,
)
from poms.transactions.tests.transaction_type_dicts import (
    TRANSACTION_TYPE_WITH_INPUTS_DICT,
    TRANSACTION_TYPE_DICT,
    TRANSACTION_TYPE_BOOK_DICT,
)

DATE_FORMAT = settings.API_DATE_FORMAT


class TransactionTypeViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/transactions/transaction-type/"

    @staticmethod
    def get_transaction_type_group() -> TransactionTypeGroup:
        return TransactionTypeGroup.objects.get(user_code__contains="unified")

    def create_transaction_type(self) -> TransactionType:
        transaction_type_group = self.get_transaction_type_group()
        self.transaction_type = TransactionType.objects.create(
            master_user=self.master_user,
            owner=self.member,
            configuration_code=self.random_string(),
            user_code=self.random_string(7),
            name=self.random_string(),
            short_name=self.random_string(3),
            group=transaction_type_group.user_code,
            type=TransactionType.TYPE_DEFAULT,
            user_text_1=self.random_string(),
            user_text_2=self.random_string(),
            user_number_1=str(self.random_int()),
            user_number_2=str(self.random_int()),
            # user_date_1=self.random_future_date().strftime(DATE_FORMAT),
            # user_date_2=self.random_future_date().strftime(DATE_FORMAT),
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
            owner=self.member,
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
            # "user_date_1": self.random_future_date().strftime(DATE_FORMAT),
        }

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__retrieve(self):
        transaction_type = self.create_transaction_type()

        response = self.client.get(path=f"{self.url}{transaction_type.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), TRANSACTION_TYPE_DICT.keys())

        # check values
        self.assertEqual(response_json["name"], transaction_type.name)
        self.assertEqual(response_json["short_name"], transaction_type.short_name)
        self.assertEqual(response_json["type"], transaction_type.type)
        self.assertEqual(
            response_json["visibility_status"],
            transaction_type.visibility_status,
        )
        self.assertEqual(
            response_json["transaction_unique_code_expr"],
            transaction_type.transaction_unique_code_expr,
        )
        self.assertEqual(response_json["user_date_1"], transaction_type.user_date_1)
        self.assertEqual(response_json["user_text_1"], transaction_type.user_text_1)
        self.assertEqual(
            int(response_json["user_number_2"]),
            int(transaction_type.user_number_2),
        )

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 64)

    def test__list_light(self):
        self.create_transaction_type()

        response = self.client.get(path=f"{self.url}light/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 6)

    def test__ev_item(self):
        self.create_transaction_type()

        response = self.client.post(path=f"{self.url}ev-item/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 6)

    def test__light_with_inputs(self):
        transaction_type = self.create_transaction_type()
        self.create_transaction_type_input(transaction_type)

        response = self.client.get(
            path=f"{self.url}light-with-inputs/?short_name={transaction_type.short_name}"
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 1)
        response_dict = response_json["results"][0]
        self.assertEqual(response_dict["short_name"], transaction_type.short_name)

        self.assertEqual(response_dict.keys(), TRANSACTION_TYPE_WITH_INPUTS_DICT.keys())

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        transaction_type = self.create_transaction_type()
        response = self.client.get(path=f"{self.url}?name={transaction_type.name}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["name"],
            transaction_type.name,
        )

        response = self.client.get(
            path=f"{self.url}?short_name={transaction_type.short_name}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["short_name"],
            transaction_type.short_name,
        )

    def test__update_patch(self):
        transaction_type = self.create_transaction_type()
        type_id = transaction_type.id

        new_name = self.random_string()
        update_data = {"name": new_name}
        response = self.client.patch(
            path=f"{self.url}{type_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{type_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["name"], new_name)

    def test__delete(self):
        transaction_type = self.create_transaction_type()
        type_id = transaction_type.id

        response = self.client.delete(path=f"{self.url}{type_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{type_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertTrue(response_json["is_deleted"])

    def test__create(self):
        create_data = self.prepare_create_data()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 201, response.content)

        transaction_type = TransactionType.objects.filter(name=create_data["user_code"])
        self.assertIsNotNone(transaction_type)

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

    def prepare_book_data(self):
        return {
            "complex_transaction_status": ComplexTransaction.SHOW_PARAMETERS,
            "process_mode": TransactionTypeProcess.MODE_BOOK,
        }

    def test__book_get(self):
        transaction_type = self.create_transaction_type()
        type_id = transaction_type.id

        response = self.client.get(path=f"{self.url}{type_id}/book/", format="json")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), TRANSACTION_TYPE_BOOK_DICT.keys())

    def test__book_put(self):
        transaction_type = self.create_transaction_type()
        type_id = transaction_type.id

        context_data = self.prepare_context_data()
        query_params = parse.urlencode(context_data, doseq=False)

        book_data = self.prepare_book_data()

        response = self.client.put(
            path=f"{self.url}{type_id}/book/?{query_params}",
            format="json",
            data=book_data,
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json.keys(), TRANSACTION_TYPE_BOOK_DICT.keys())

    @skip("'ComplexTransaction' instance needs to have a primary key value ...")
    def test__book_pending_get(self):
        transaction_type = self.create_transaction_type()
        type_id = transaction_type.id

        response = self.client.get(
            path=f"{self.url}{type_id}/book-pending/",
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), TRANSACTION_TYPE_BOOK_DICT.keys())

    def test__book_pending_put(self):
        transaction_type = self.create_transaction_type()
        type_id = transaction_type.id

        context_data = self.prepare_context_data()
        query_params = parse.urlencode(context_data, doseq=False)

        book_data = self.prepare_book_data()

        response = self.client.put(
            path=f"{self.url}{type_id}/book-pending/?{query_params}",
            format="json",
            data=book_data,
        )
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        self.assertEqual(response_json.keys(), TRANSACTION_TYPE_BOOK_DICT.keys())
