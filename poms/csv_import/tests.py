from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .views import CsvDataImportViewSet
from .models import Scheme, CsvField, EntityField
from django.contrib.auth.models import User
from poms.users.models import MasterUser

from poms.counterparties.models import Responsible
from poms.accounts.models import AccountType, Account
from poms.portfolios.models import Portfolio

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute
from poms.integrations.models import AccountMapping, ResponsibleMapping, ProviderClass

from .tests_data import TestData

import logging

logger = logging.getLogger('django_test')


class CsvImportTestCase(TestCase):

    def setUp(self):
        user = User.objects.create_user('a1')
        self.master_user = MasterUser.objects.create_master_user(user=user, name='a1_m1')

        self.at1 = AccountType.objects.create(master_user=self.master_user, name='at1', show_transaction_details=False)
        self.ac1 = Account.objects.create(master_user=self.master_user, name='ac1', type=self.at1)
        self.res1 = Responsible.objects.create(master_user=self.master_user, name='res1')

        self.dynamic_attr_string = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                       name="Country",
                                                                       value_type=GenericAttributeType.STRING,
                                                                       content_type=ContentType.objects.get_for_model(
                                                                           Portfolio))
        self.dynamic_attr_number = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                       name="Num",
                                                                       value_type=GenericAttributeType.NUMBER,
                                                                       content_type=ContentType.objects.get_for_model(
                                                                           Portfolio)
                                                                       )
        self.dynamic_attr_date = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                     name="Date",
                                                                     value_type=GenericAttributeType.DATE,
                                                                     content_type=ContentType.objects.get_for_model(
                                                                         Portfolio))

        bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)

        self.res1Map = ResponsibleMapping.objects.create(master_user=self.master_user, provider=bloomberg,
                                                         content_object=self.res1, value='res_1')
        self.ac1Map = AccountMapping.objects.create(master_user=self.master_user, provider=bloomberg,
                                                    content_object=self.ac1, value='account_2')

        self.scheme = self._create_scheme()

        pass

    def _create_scheme(self):

        scheme = Scheme.objects.create(name="Portfolio scheme", content_type=ContentType.objects.get_for_model(Portfolio))

        CsvField.objects.create(column=0, value="name", scheme=scheme)
        CsvField.objects.create(column=1, value="short_name", scheme=scheme)
        CsvField.objects.create(column=2, value="account", scheme=scheme)
        CsvField.objects.create(column=3, value="country", scheme=scheme)
        CsvField.objects.create(column=4, value="date", scheme=scheme)
        CsvField.objects.create(column=5, value="num", scheme=scheme)
        CsvField.objects.create(column=6, value="responsible", scheme=scheme)

        EntityField.objects.create(name="Name", expression="name", system_property_key="name", scheme=scheme)
        EntityField.objects.create(name="Short name", expression="short_name", system_property_key="short_name",  scheme=scheme)
        EntityField.objects.create(name="Notes", expression="", system_property_key="notes", scheme=scheme)
        EntityField.objects.create(name="public name", expression="", system_property_key="public_name", scheme=scheme)
        EntityField.objects.create(name="User code", expression="name + '_us1'", system_property_key="user_code", scheme=scheme)
        EntityField.objects.create(name="Accounts", expression="account", system_property_key="accounts", scheme=scheme)
        EntityField.objects.create(name="Responsibles", expression="responsible", system_property_key="responsibles", scheme=scheme)
        EntityField.objects.create(name="Counterparties", expression="", system_property_key="counterparties", scheme=scheme)

        EntityField.objects.create(name="Test number", expression="num", dynamic_attribute_id=self.dynamic_attr_number.id, scheme=scheme)
        EntityField.objects.create(name="Test Date", expression="date", dynamic_attribute_id=self.dynamic_attr_date.id, scheme=scheme)
        EntityField.objects.create(name="Country", expression="country", dynamic_attribute_id=self.dynamic_attr_string.id, scheme=scheme)

        return Scheme.objects.get(pk=scheme.id)

    def test_scheme_create(self):
        return self._create_scheme()

    def test_case_correct_file(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_columns_in_file_less_then_in_scheme(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.correct_small_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and small File produces 0 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_user_code_already_exists(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        self.assertEqual(len(process_errors), 4)

    def test_case_relation_invalid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.error_relation_mapping_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and incorrect File produces 3 errors

        self.assertEqual(len(process_errors), 3)

        pass

    def test_case_error_handler_break(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'break'

        rows = TestData.error_relation_mapping_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and incorrect File produces 3 errors

        self.assertEqual(len(process_errors), 1)

        pass

    def test_case_error_handler_continue(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.error_relation_mapping_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and incorrect File produces 3 errors

        self.assertEqual(len(process_errors), 3)

        pass

    def test_case_expression_invalid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, system_property_key='user_code')
        invalid_field.expression = "name + '_us1' / 0"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and incorrect File produces 4 errors

        self.assertEqual(len(process_errors), 4)

        pass

    def test_case_dynamic_attribute_date_expression_valid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_date.id)
        invalid_field.expression = "format_date(date)"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_dynamic_attribute_number_expression_valid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_number.id)
        invalid_field.expression = "float(num) * 0.23"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_dynamic_attribute_string_expression_valid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_string.id)
        invalid_field.expression = "country + ' risk'"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_dynamic_attribute_date_expression_invalid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_date.id)
        invalid_field.expression = "format_date(date, format='%m-%Y-%d')"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_dynamic_attribute_number_expression_invalid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_number.id)
        invalid_field.expression = "num / 0"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_dynamic_attribute_number_expression_invalid2(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_number.id)
        invalid_field.expression = "country"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_dynamic_attribute_string_expression_invalid(self):

        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme, dynamic_attribute_id=self.dynamic_attr_string.id)
        invalid_field.expression = "country ////"
        invalid_field.save()

        self.scheme = Scheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)