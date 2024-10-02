from poms.common.common_base_test import BaseTestCase
from poms.integrations.tasks import create_currency_from_callback_data


test_cases =[
    {
        'id': 4,
        'user_code': 'DZD',
        'short_name': 'DZD',
        'name': 'Algerian Dinar (DZD)',
        'public_name': None,
        'numeric_code': '012',
        'country': 'DZA',
    },
    {
        'id': 4,
        'user_code': 'DZD',
        'short_name': 'DZD',
        'name': 'Algerian Dinar (DZD)',
        'public_name': None,
        'numeric_code': '012',
        'country': None,
    },
    {
        'id': 4,
        'user_code': 'DZD',
        'short_name': 'DZD',
        'name': 'Algerian Dinar (DZD)',
        'public_name': None,
        'numeric_code': '012',
        'country': 'NotCorrect',
    },
] 


currency_with_county = {
    'id': 4,
    'user_code': 'DZD',
    'short_name': 'DZD',
    'name': 'Algerian Dinar (DZD)',
    'public_name': None,
    'numeric_code': '012',
    'country.alpha_3': "DZA",
}


currency_without_county = {
    'id': 4,
    'user_code': 'DZD',
    'short_name': 'DZD',
    'name': 'Algerian Dinar (DZD)',
    'public_name': None,
    'numeric_code': '012',
    'country': None,
}


class CurrensyFromRespDataTest(BaseTestCase):
    databases = "__all__"

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.user_code = self.random_string()

    def test__with_country(self):
        data = test_cases[0]
        currency = create_currency_from_callback_data(data, self.master_user, self.member)
        self.assertEqual(currency.user_code, currency_with_county["user_code"])
        self.assertEqual(currency.country.alpha_3, currency_with_county["country.alpha_3"])

    def test__without_country(self):
        data = test_cases[1]
        currency = create_currency_from_callback_data(data, self.master_user, self.member)
        self.assertEqual(currency.user_code, currency_with_county["user_code"])
        self.assertIsNone(currency.country)

        data = test_cases[2]
        currency = create_currency_from_callback_data(data, self.master_user, self.member)
        self.assertEqual(currency.user_code, currency_with_county["user_code"])
        self.assertIsNone(currency.country)
