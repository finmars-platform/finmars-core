from poms.common.common_base_test import BIG, BaseTestCase
from poms.transactions.models import (
    ComplexTransaction,
    ComplexTransactionInput,
    ComplexTransactionStatus,
    Transaction,
    TransactionType,
    TransactionTypeGroup,
    TransactionTypeInput,
)
from poms.transactions.tests.transaction_test_data import (
    EXPECTED_COMPLEX_TRANSACTION,
)


class ComplexTransactionViewSetTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.realm_code = "realm00000"
        self.space_code = "space00000"
        self.url = f"/{self.realm_code}/{self.space_code}/api/v1/transactions/complex-transaction/"

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
            owner=self.member,
            user_code=self.random_string(7),
            name=self.random_string(),
        )

    def create_transaction_type(self) -> TransactionType:
        transaction_type_group = self.create_transaction_type_group()
        self.transaction_type = TransactionType.objects.create(
            master_user=self.master_user,
            owner=self.member,
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
            owner=self.member,
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
        response = self.client.post(path=self.url, format="json", data={})
        self.assertEqual(response.status_code, 400, response.content)

    def test__update_patch(self):
        complex_transaction = self.create_complex_transaction()
        transaction_id = complex_transaction.id

        new_code = self.random_int()
        update_data = {"code": new_code}
        response = self.client.patch(
            path=f"{self.url}{transaction_id}/", format="json", data=update_data
        )
        self.assertEqual(response.status_code, 200, response.content)

        response = self.client.get(path=f"{self.url}{transaction_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()
        self.assertEqual(response_json["code"], new_code)

    def test__delete(self):
        complex_transaction = self.create_complex_transaction()
        transaction_id = complex_transaction.id

        response = self.client.delete(path=f"{self.url}{transaction_id}/")
        self.assertEqual(response.status_code, 204, response.content)

        response = self.client.get(path=f"{self.url}{transaction_id}/")
        self.assertEqual(response.status_code, 200, response.content)
        response_json = response.json()

        self.assertTrue(response_json["is_deleted"])

    def test__fake_delete_complex_transaction(self):
        portfolio = self.db_data.portfolios[BIG]

        self.assertIsNone(Transaction.objects.filter(portfolio=portfolio).first())
        self.assertIsNone(portfolio.first_transaction_date)
        self.assertIsNone(portfolio.first_cash_flow_date)

        complex_transaction, transaction = self.db_data.cash_in_transaction(
            portfolio,
            day=self.random_future_date(),
        )
        self.assertIsNotNone(portfolio.first_transaction_date)
        self.assertIsNotNone(portfolio.first_cash_flow_date)
        self.assertFalse(complex_transaction.is_deleted)

        # 1st time - fake delete, but base transactions - should be deleted
        complex_transaction.fake_delete()

        portfolio.refresh_from_db()
        self.assertTrue(complex_transaction.is_deleted)
        self.assertIsNone(Transaction.objects.filter(pk=transaction.id).first())
        self.assertIsNone(portfolio.first_transaction_date)
        self.assertIsNone(portfolio.first_cash_flow_date)

        # 2nd time - real delete
        complex_transaction.fake_delete()

        self.assertIsNone(
            ComplexTransaction.objects.filter(pk=complex_transaction.id).first()
        )
