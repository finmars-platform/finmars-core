from unittest import mock
from poms.instruments.models import Country
from poms.common.common_base_test import BaseTestCase
from poms.users.models import MasterUser, Member
from poms.currencies.models import Currency


correct_mock_currencies_data = [
    {
        "user_code": "CHF",
        "name": "Swiss Franc (CHF)",
        "country_alpha_3": "CHE"
    },
    {
        "user_code": "GBP",
        "name": "Pound Sterling (GBP)",
        "country_alpha_3": "GBR"
    }
]
        
not_correct_mock_currencies_data = [
    {
        "user_code": "CHF",
        "name": "Swiss Franc (CHF)",
        "country_alpha_3": "TT"
    },
    {
        "user_code": "GBP",
        "name": "Pound Sterling (GBP)",
        "country_alpha_3": ""
    }
]


class CreateDefaultCurrenciesTestCase(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()

    @mock.patch('poms.currencies.models.currencies_data', new_callable=mock.MagicMock)
    def test__upload_correct_data(self, mock_currencies_data):
        mock_currencies_data.values.return_value = correct_mock_currencies_data
        _ = self.master_user.create_defaults_currencies(self.member)
            
        currency = Currency.objects.get(user_code="CHF")
        self.assertEqual(currency.name, "Swiss Franc (CHF)")
        self.assertEqual(currency.country.alpha_3, "CHE")
        
        currency = Currency.objects.get(user_code="GBP")
        self.assertEqual(currency.name, "Pound Sterling (GBP)")
        self.assertEqual(currency.country.alpha_3, "GBR")

    @mock.patch('poms.currencies.models.currencies_data', new_callable=mock.MagicMock)
    def test__upload_not_correct_data(self, mock_currencies_data):
        mock_currencies_data.values.return_value = not_correct_mock_currencies_data

        with self.assertRaises(Country.DoesNotExist):
            _ = self.master_user.create_defaults_currencies(self.member)
