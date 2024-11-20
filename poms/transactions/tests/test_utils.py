from poms.common.common_base_test import BaseTestCase

from poms.transactions.utils import generate_user_fields, MAX_TEXT, MAX_DATE, MAX_NUMBER

class TestUtils(BaseTestCase):

    def test_default_length(self):
        fields = generate_user_fields()
        self.assertEqual(len(fields), MAX_TEXT + MAX_NUMBER + MAX_DATE)

    def test_provided_length(self):
        fields = generate_user_fields(max_text=1, max_number=1, max_date=1)
        self.assertEqual(len(fields), 3)

    def test_text_length(self):
        fields = generate_user_fields()
        count = 0
        for field in fields:
            if field.startswith("user_text_"):
                count += 1
        self.assertEqual(count, MAX_TEXT)

    def test_number_length(self):
        fields = generate_user_fields()
        count = 0
        for field in fields:
            if field.startswith("user_number_"):
                count += 1
        self.assertEqual(count, MAX_NUMBER)

    def test_date_length(self):
        fields = generate_user_fields()
        count = 0
        for field in fields:
            if field.startswith("user_date_"):
                count += 1
        self.assertEqual(count, MAX_DATE)
