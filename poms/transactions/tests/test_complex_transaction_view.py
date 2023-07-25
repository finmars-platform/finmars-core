from copy import deepcopy
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from poms.common.common_base_test import BaseTestCase
from poms.transactions.models import (
    ComplexTransaction,
    ComplexTransactionInput,
    ComplexTransactionStatus,
    TransactionType,
    TransactionTypeGroup,
    TransactionTypeInput,
)


from poms.obj_attrs.models import GenericAttribute, GenericAttributeType

EXPECTED_COMPLEX_TRANSACTION = {
    "id": 1,
    "date": "2023-10-23",
    "status": 2,
    "code": 100,
    "text": None,
    "transaction_type": 13,
    "transactions": [],
    "transaction_unique_code": "87648176382763",
    "is_locked": False,
    "is_canceled": False,
    "error_code": None,
    "is_deleted": False,
    "user_text_1": "QKARGVBJML",
    "user_text_2": "VMBKMMTZPB",
    "user_text_3": None,
    "user_text_4": None,
    "user_text_5": None,
    "user_text_6": None,
    "user_text_7": None,
    "user_text_8": None,
    "user_text_9": None,
    "user_text_10": None,
    "user_text_11": None,
    "user_text_12": None,
    "user_text_13": None,
    "user_text_14": None,
    "user_text_15": None,
    "user_text_16": None,
    "user_text_17": None,
    "user_text_18": None,
    "user_text_19": None,
    "user_text_20": None,
    "user_text_21": None,
    "user_text_22": None,
    "user_text_23": None,
    "user_text_24": None,
    "user_text_25": None,
    "user_text_26": None,
    "user_text_27": None,
    "user_text_28": None,
    "user_text_29": None,
    "user_text_30": None,
    "user_number_1": None,
    "user_number_2": None,
    "user_number_3": None,
    "user_number_4": None,
    "user_number_5": None,
    "user_number_6": None,
    "user_number_7": None,
    "user_number_8": None,
    "user_number_9": None,
    "user_number_10": None,
    "user_number_11": None,
    "user_number_12": None,
    "user_number_13": None,
    "user_number_14": None,
    "user_number_15": None,
    "user_number_16": None,
    "user_number_17": None,
    "user_number_18": None,
    "user_number_19": None,
    "user_number_20": None,
    "user_date_1": None,
    "user_date_2": None,
    "user_date_3": None,
    "user_date_4": None,
    "user_date_5": None,
    "recon_fields": [],
    "execution_log": None,
    "source": None,
    "inputs": [],
    "attributes": [
        {
            "id": 2,
            "attribute_type": 2,
            "value_string": "ELQMDDKLRI",
            "value_float": 1289.0,
            "value_date": "2023-07-24",
            "classifier": None,
            "attribute_type_object": {
                "id": 2,
                "user_code": "local.poms.space00000:auth.permission:skbii",
                "name": "",
                "short_name": "CC",
                "public_name": None,
                "notes": None,
                "can_recalculate": False,
                "value_type": 20,
                "order": 0,
                "is_hidden": False,
                "kind": 1,
            },
            "classifier_object": None,
        }
    ],
    "transaction_type_object": {
        "id": 13,
        "group": 5,
        "user_code": "local.poms.space00000:kpprwgt",
        "name": "MYTRGYVSEZ",
        "short_name": "CKQ",
        "public_name": None,
        "notes": None,
        "is_valid_for_all_portfolios": True,
        "is_valid_for_all_instruments": True,
        "is_deleted": False,
        "transaction_unique_code_expr": "WYDRYHRAMX",
        "transaction_unique_code_options": 3,
        "user_text_1": "ACEUWUDLUO",
        "user_text_2": "TLUEHXJRAE",
        "user_text_3": "",
        "user_text_4": "",
        "user_text_5": "",
        "user_text_6": "",
        "user_text_7": "",
        "user_text_8": "",
        "user_text_9": "",
        "user_text_10": "",
        "user_text_11": "",
        "user_text_12": "",
        "user_text_13": "",
        "user_text_14": "",
        "user_text_15": "",
        "user_text_16": "",
        "user_text_17": "",
        "user_text_18": "",
        "user_text_19": "",
        "user_text_20": "",
        "user_text_21": "",
        "user_text_22": "",
        "user_text_23": "",
        "user_text_24": "",
        "user_text_25": "",
        "user_text_26": "",
        "user_text_27": "",
        "user_text_28": "",
        "user_text_29": "",
        "user_text_30": "",
        "user_number_1": "EIGSNVITEP",
        "user_number_2": "CRSMCTSCZL",
        "user_number_3": "",
        "user_number_4": "",
        "user_number_5": "",
        "user_number_6": "",
        "user_number_7": "",
        "user_number_8": "",
        "user_number_9": "",
        "user_number_10": "",
        "user_number_11": "",
        "user_number_12": "",
        "user_number_13": "",
        "user_number_14": "",
        "user_number_15": "",
        "user_number_16": "",
        "user_number_17": "",
        "user_number_18": "",
        "user_number_19": "",
        "user_number_20": "",
        "user_date_1": "2024-01-21",
        "user_date_2": "2024-05-31",
        "user_date_3": "",
        "user_date_4": "",
        "user_date_5": "",
        "deleted_user_code": None,
        "meta": {
            "content_type": "transactions.transactiontype",
            "app_label": "transactions",
            "model_name": "transactiontype",
            "space_code": "space00000",
        },
        "group_object": {
            "id": 5,
            "user_code": "local.poms.space00000:lzzrpsw",
            "name": "YXJHQKXBUH",
            "short_name": "YXJHQKXBUH",
            "public_name": None,
            "notes": None,
            "is_deleted": False,
            "deleted_user_code": None,
            "meta": {
                "content_type": "transactions.transactiontypegroup",
                "app_label": "transactions",
                "model_name": "transactiontypegroup",
                "space_code": "space00000",
            },
        },
    },
    "transactions_object": [],
    "meta": {
        "content_type": "transactions.complextransaction",
        "app_label": "transactions",
        "model_name": "complextransaction",
        "space_code": "space00000",
    },
}

CREATE_DATA = {
    "date": "2023-07-30",
    "code": 1273645,
    "transaction_unique_code": "7165347157",
    "transaction_type": 0,
    "visibility_status": ComplexTransaction.HIDE_PARAMETERS,
    "user_text_1": "iqyweiquyei",
    "user_number_1": "27364",
    "user_date_1": "2025-03-03",
}


class InstrumentViewSetTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = f"/{settings.BASE_API_URL}/api/v1/transactions/complex-transaction/"

    def create_attribute_type(self) -> GenericAttributeType:
        self.attribute_type = GenericAttributeType.objects.create(
            master_user=self.master_user,
            content_type=ContentType.objects.first(),
            user_code=self.random_string(5),
            short_name=self.random_string(2),
            value_type=GenericAttributeType.NUMBER,
            kind=GenericAttributeType.USER,
            tooltip=self.random_string(),
            favorites=self.random_string(),
            prefix=self.random_string(3),
            expr=self.random_string(),
        )
        return self.attribute_type

    def create_attribute(self) -> GenericAttribute:
        self.attribute = GenericAttribute.objects.create(
            attribute_type=self.create_attribute_type(),
            content_type=ContentType.objects.last(),
            object_id=self.random_int(),
            value_string=self.random_string(),
            value_float=self.random_int(),
            value_date=date.today(),
        )
        return self.attribute

    @staticmethod
    def get_complex_transaction_status(model_id=ComplexTransaction.PENDING):
        return ComplexTransactionStatus.objects.get(id=model_id)

    def create_complex_transaction_input(self, transaction: ComplexTransaction):
        return ComplexTransactionInput.objects.create(
            complex_transaction=transaction,
        )

    def create_transaction_type_group(self) -> TransactionTypeGroup:
        return TransactionTypeGroup.objects.create(
            master_user=self.master_user,
            user_code=self.random_string(7),
            name=self.random_string(),
        )

    def create_transaction_type(self) -> TransactionType:
        transaction_type_group = self.create_transaction_type_group()
        self.transaction_type = TransactionType.objects.create(
            master_user=self.master_user,
            user_code=self.random_string(7),
            name=self.random_string(),
            short_name=self.random_string(3),
            group=transaction_type_group.user_code,
            transaction_unique_code_expr=self.random_string(),
            transaction_unique_code_options=TransactionType.OVERWRITE,
            type=TransactionType.TYPE_DEFAULT,
            visibility_status=TransactionType.SHOW_PARAMETERS,
            user_text_1=self.random_string(),
            user_text_2=self.random_string(),
            user_number_1=str(self.random_int()),
            user_number_2=str(self.random_int()),
            user_date_1=str(self.random_future_date()),
            user_date_2=str(self.random_future_date()),
            is_deleted=False,
        )
        self.transaction_type.attributes.add(self.create_attribute())
        self.transaction_type.book_transaction_layout = {"test": "test"}
        self.transaction_type.save()
        return self.transaction_type

    def create_complex_transaction(self) -> ComplexTransaction:
        self.transaction = ComplexTransaction.objects.create(
            # mandatory fields
            master_user=self.master_user,
            transaction_type=self.create_transaction_type(),
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
        self.transaction.attributes.add(self.create_attribute())
        self.transaction.save()

        return self.transaction

    def create_transaction_type_input(self, transaction_type) -> TransactionTypeInput:
        return TransactionTypeInput.objects.create(
            transaction_type=transaction_type,
            name=self.random_string(),
        )

    def prepare_data_for_create(self) -> dict:
        create_data = deepcopy(CREATE_DATA)
        create_data["attributes"] = []
        transaction_type = self.create_transaction_type()
        create_data["transaction_type"] = transaction_type.id
        transaction_type_input = self.create_transaction_type_input(transaction_type)
        create_data["inputs"] = [
            {
                "transaction_type_input": transaction_type_input.id,
                "transaction_type_input_object": {
                    "transaction_type": transaction_type.id,
                    "name": transaction_type_input.name,
                    "tooltip": self.random_string(),
                    "settings": None,
                    "content_type": None,
                },
            }
        ]
        return create_data

    def test__check_api_url(self):
        response = self.client.get(path=self.url)
        self.assertEqual(response.status_code, 200, response.content)

    def test__retrieve(self):
        complex_transaction = self.create_complex_transaction()
        response = self.client.get(path=f"{self.url}{complex_transaction.id}/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()

        # check fields
        self.assertEqual(response_json.keys(), EXPECTED_COMPLEX_TRANSACTION.keys())

        # check values
        self.assertEqual(response_json["status"], complex_transaction.status.id)
        self.assertEqual(
            response_json["transaction_unique_code"],
            complex_transaction.transaction_unique_code,
        )
        self.assertEqual(
            response_json["transaction_type"],
            complex_transaction.transaction_type.id,
        )
        self.assertEqual(
            response_json["user_text_1"],
            complex_transaction.user_text_1,
        )
        self.assertEqual(
            int(response_json["user_number_2"]),
            int(complex_transaction.user_number_2),
        )
        self.assertEqual(
            response_json["user_date_1"],
            complex_transaction.user_date_1,
        )

    def test__list_attributes(self):
        response = self.client.get(path=f"{self.url}attributes/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 63)

    def test__list_light(self):
        self.create_complex_transaction()
        response = self.client.get(path=f"{self.url}light/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 1)

    def test__view(self):
        complex_transaction = self.create_complex_transaction()
        response = self.client.get(path=f"{self.url}{complex_transaction.id}/view/")
        self.assertEqual(response.status_code, 200, response.content)

    def test__bulk_restore_get(self):
        self.create_complex_transaction()
        response = self.client.get(path=f"{self.url}bulk-restore/")
        self.assertEqual(response.status_code, 200, response.content)

        response_json = response.json()
        self.assertEqual(len(response_json["results"]), 1)

    def test__get_filters(self):  # sourcery skip: extract-duplicate-method
        complex_transaction = self.create_complex_transaction()
        response = self.client.get(path=f"{self.url}?code={complex_transaction.code}")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["code"],
            complex_transaction.code,
        )

        response = self.client.get(
            path=f"{self.url}?is_deleted={complex_transaction.is_deleted}"
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["count"], 1)
        self.assertEqual(
            response_json["results"][0]["is_deleted"],
            complex_transaction.is_deleted,
        )

    def test__create(self):
        create_data = self.prepare_data_for_create()

        response = self.client.post(path=self.url, format="json", data=create_data)
        self.assertEqual(response.status_code, 400, response.content)

    # def test__update_patch(self):
    #     create_data = self.prepare_data_for_create()
    #
    #     response = self.client.post(path=self.url, format="json", data=create_data)
    #     self.assertEqual(response.status_code, 201, response.content)
    #     response_json = response.json()
    #
    #     transaction_id = response_json["id"]
    #     new_user_text_1 = self.random_string()
    #     update_data = {"user_text_1": new_user_text_1}
    #     response = self.client.patch(
    #         path=f"{self.url}{transaction_id}/", format="json", data=update_data
    #     )
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     response = self.client.get(path=f"{self.url}{transaction_id}/")
    #     self.assertEqual(response.status_code, 200, response.content)
    #     response_json = response.json()
    #     self.assertEqual(response_json["user_text_1"], new_user_text_1)
    #
    # def test__delete(self):
    #     create_data = self.prepare_data_for_create()
    #
    #     response = self.client.post(path=self.url, format="json", data=create_data)
    #     self.assertEqual(response.status_code, 201, response.content)
    #     response_json = response.json()
    #
    #     transaction_id = response_json["id"]
    #
    #     response = self.client.delete(path=f"{self.url}{transaction_id}/")
    #     self.assertEqual(response.status_code, 204, response.content)
    #
    #     response = self.client.get(path=f"{self.url}{transaction_id}/")
    #     self.assertEqual(response.status_code, 200, response.content)
    #     response_json = response.json()
    #
    #     self.assertTrue(response_json["is_deleted"])
