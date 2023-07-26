from django.conf import settings

from poms.common.common_base_test import BaseTestCase
from poms.transactions.models import (
    TransactionType,
    TransactionTypeGroup,
    TransactionTypeInput,
    TransactionTypeInputSettings,
)

EXPECTED_TRANSACTION_TYPE = {
    "id": 26,
    "group": 10,
    "user_code": "local.poms.space00000:ksyvcrp",
    "name": "DMXOVPNWKG",
    "short_name": "UVK",
    "public_name": None,
    "notes": None,
    "date_expr": "",
    "display_expr": "",
    "visibility_status": 1,
    "type": 1,
    "transaction_unique_code_expr": "QTIVCWLRRG",
    "transaction_unique_code_options": 3,
    "user_text_1": "ZGRCADCBWU",
    "user_text_2": "NQPFFFXMKA",
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
    "user_number_1": "5202",
    "user_number_2": "2079",
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
    "user_date_1": "2024-03-26",
    "user_date_2": "2023-09-20",
    "user_date_3": "",
    "user_date_4": "",
    "user_date_5": "",
    "is_valid_for_all_portfolios": True,
    "is_valid_for_all_instruments": True,
    "is_deleted": False,
    "book_transaction_layout": {"test": "test"},
    "instrument_types": [],
    "portfolios": [],
    "inputs": [],
    "actions": [],
    "recon_fields": [],
    "context_parameters": [],
    "context_parameters_notes": None,
    "is_enabled": True,
    "configuration_code": "local.poms.space00000",
    "attributes": [
        {
            "id": 2,
            "attribute_type": 2,
            "value_string": "NRNFLUWEZS",
            "value_float": 9207.0,
            "value_date": "2023-07-26",
            "classifier": None,
            "attribute_type_object": {
                "id": 2,
                "user_code": "local.poms.space00000:auth.permission:tkwkb",
                "name": "",
                "short_name": "IV",
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
    "deleted_user_code": None,
    "instrument_types_object": [],
    "portfolios_object": [],
    "meta": {
        "content_type": "transactions.transactiontype",
        "app_label": "transactions",
        "model_name": "transactiontype",
        "space_code": "space00000",
    },
    "group_object": {
        "id": 10,
        "user_code": "local.poms.space00000:ranorwp",
        "name": "XLQMQEQYZS",
        "short_name": "XLQMQEQYZS",
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
}


class InstrumentViewSetTest(BaseTestCase):
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
            user_date_1=str(self.random_future_date()),
            user_date_2=str(self.random_future_date()),
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

    def prepare_create_data(self) -> dict:
        # instrument_id = request.query_params.get("context_instrument", None)
        # pricing_currency_id = request.query_params.get("context_pricing_currency", None)
        # accrued_currency_id = request.query_params.get("context_accrued_currency", None)
        # portfolio_id = request.query_params.get("context_portfolio", None)
        # account_id = request.query_params.get("context_account", None)
        # strategy1_id = request.query_params.get("context_strategy1", None)
        # strategy2_id = request.query_params.get("context_strategy2", None)
        # strategy3_id = request.query_params.get("context_strategy3", None)
        #
        # currency_id = request.query_params.get("context_currency", None)
        # pricing_policy_id = request.query_params.get("context_pricing_policy", None)
        # allocation_balance_id = request.query_params.get(
        #     "context_allocation_balance", None
        # )
        # allocation_pl_id = request.query_params.get("context_allocation_pl", None)

        transaction_type_group = self.get_transaction_type_group()
        return {
            "group": transaction_type_group.user_code,
            "configuration_code": self.random_string(),
            "user_code": self.random_string(7),
            "name": self.random_string(),
            "short_name": self.random_string(3),
            "user_text_1": self.random_string(),
            "user_number_1": str(self.random_int()),
            "user_date_1": str(self.random_future_date()),
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
        self.assertEqual(response_json.keys(), EXPECTED_TRANSACTION_TYPE.keys())

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
        self.assertEqual(len(response_json["results"]), 7)

    # def test__light_with_inputs(self):
    #     # FIXME Field name `group_object` is not valid for model `TransactionType`
    #     transaction_type = self.create_transaction_type()
    #     self.create_transaction_type_input(transaction_type)
    #
    #     response = self.client.get(path=f"{self.url}light-with-inputs/")
    #     self.assertEqual(response.status_code, 200, response.content)
    #
    #     response_json = response.json()
    #
    #     print(response_json)

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

        new_name= self.random_string()
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
