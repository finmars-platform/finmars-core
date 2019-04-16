from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .views import CsvDataImportViewSet
from .models import CsvImportScheme, CsvField, EntityField
from django.contrib.auth.models import User
from poms.users.models import MasterUser

from poms.counterparties.models import Responsible, Counterparty
from poms.accounts.models import AccountType, Account
from poms.portfolios.models import Portfolio

from poms.obj_attrs.models import GenericAttributeType, GenericAttribute, GenericClassifier
from poms.integrations.models import AccountMapping, ResponsibleMapping, PortfolioMapping, CounterpartyMapping, \
    ProviderClass, PortfolioClassifierMapping

from .tests_data import TestData

import logging

logger = logging.getLogger('django_test')


class CsvImportTestCase(TestCase):

    def setUp(self):
        user = User.objects.create_user('a1')
        self.master_user = MasterUser.objects.create_master_user(user=user, name='a1_m1')

        self.default_p1 = Portfolio.objects.get(master_user=self.master_user, user_code='-')
        self.at1 = AccountType.objects.create(master_user=self.master_user, name='at1', show_transaction_details=False)
        self.ac1 = Account.objects.create(master_user=self.master_user, name='ac1', type=self.at1)
        self.res1 = Responsible.objects.create(master_user=self.master_user, name='res1')

        self.bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)

        self.setPortfolioDynamicAttrs()
        self.setAccountDynamicAttrs()
        self.setResponsibleDynamicAttrs()
        self.setCounterpartyDynamicAttrs()

        self.res1_map = ResponsibleMapping.objects.create(master_user=self.master_user, provider=self.bloomberg,
                                                          content_object=self.res1, value='res_1')
        self.ac1_map = AccountMapping.objects.create(master_user=self.master_user, provider=self.bloomberg,
                                                     content_object=self.ac1, value='account_2')

        self.default_p1_map = PortfolioMapping.objects.create(master_user=self.master_user, provider=self.bloomberg,
                                                              content_object=self.default_p1, value='-')

        self.scheme = self.create_portfolio_scheme()
        self.portfolio_scheme = self.create_portfolio_scheme()
        self.account_scheme = self.create_account_scheme()
        self.counterparty_scheme = self.create_counterparty_scheme()
        self.responsible_scheme = self.create_responsible_scheme()

    def setPortfolioDynamicAttrs(self):
        self.portfolio_dynamic_attr_string = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                 name="Portfolio Country",
                                                                                 value_type=GenericAttributeType.STRING,
                                                                                 content_type=ContentType.objects.get_for_model(
                                                                                     Portfolio))
        self.portfolio_dynamic_attr_number = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                 name="Portfolio Num",
                                                                                 value_type=GenericAttributeType.NUMBER,
                                                                                 content_type=ContentType.objects.get_for_model(
                                                                                     Portfolio)
                                                                                 )
        self.portfolio_dynamic_attr_date = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                               name="Portfolio Date",
                                                                               value_type=GenericAttributeType.DATE,
                                                                               content_type=ContentType.objects.get_for_model(
                                                                                   Portfolio))
        self.portfolio_dynamic_attr_classifier = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                     name="Portfolio Country (Classifier)",
                                                                                     value_type=GenericAttributeType.CLASSIFIER,
                                                                                     content_type=ContentType.objects.get_for_model(
                                                                                         Portfolio))

        self.portfolio_classifier_russia = GenericClassifier.objects.create(
            attribute_type=self.portfolio_dynamic_attr_classifier, name="Russia")
        self.portfolio_classifier_usa = GenericClassifier.objects.create(
            attribute_type=self.portfolio_dynamic_attr_classifier, name="USA")
        self.portfolio_classifier_germany = GenericClassifier.objects.create(
            attribute_type=self.portfolio_dynamic_attr_classifier, name="Germany")

        self.portfolio_classifier_russia_map = PortfolioClassifierMapping.objects.create(master_user=self.master_user,
                                                                                         provider=self.bloomberg,
                                                                                         attribute_type=self.portfolio_dynamic_attr_classifier,
                                                                                         content_object=self.portfolio_classifier_russia,
                                                                                         value='ru')

        self.portfolio_classifier_usa_map = PortfolioClassifierMapping.objects.create(master_user=self.master_user,
                                                                                      provider=self.bloomberg,
                                                                                      attribute_type=self.portfolio_dynamic_attr_classifier,
                                                                                      content_object=self.portfolio_classifier_usa,
                                                                                      value='us')

        self.portfolio_classifier_germany_map = PortfolioClassifierMapping.objects.create(master_user=self.master_user,
                                                                                          provider=self.bloomberg,
                                                                                          attribute_type=self.portfolio_dynamic_attr_classifier,
                                                                                          content_object=self.portfolio_classifier_germany,
                                                                                          value='de')

    def setAccountDynamicAttrs(self):
        self.account_dynamic_attr_string = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                               name="Password",
                                                                               value_type=GenericAttributeType.STRING,
                                                                               content_type=ContentType.objects.get_for_model(
                                                                                   Account))
        self.account_dynamic_attr_number = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                               name="PIN",
                                                                               value_type=GenericAttributeType.NUMBER,
                                                                               content_type=ContentType.objects.get_for_model(
                                                                                   Account)
                                                                               )
        self.account_dynamic_attr_date = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                             name="Op Date",
                                                                             value_type=GenericAttributeType.DATE,
                                                                             content_type=ContentType.objects.get_for_model(
                                                                                 Account))

    def setResponsibleDynamicAttrs(self):
        self.responsible_dynamic_attr_string = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                   name="Responsible Country",
                                                                                   value_type=GenericAttributeType.STRING,
                                                                                   content_type=ContentType.objects.get_for_model(
                                                                                       Responsible))
        self.responsible_dynamic_attr_number = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                   name="Responsible Num",
                                                                                   value_type=GenericAttributeType.NUMBER,
                                                                                   content_type=ContentType.objects.get_for_model(
                                                                                       Responsible)
                                                                                   )
        self.responsible_dynamic_attr_date = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                 name="Responsible Date",
                                                                                 value_type=GenericAttributeType.DATE,
                                                                                 content_type=ContentType.objects.get_for_model(
                                                                                     Responsible))

    def setCounterpartyDynamicAttrs(self):
        self.counterparty_dynamic_attr_string = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                    name="Counterparty Country",
                                                                                    value_type=GenericAttributeType.STRING,
                                                                                    content_type=ContentType.objects.get_for_model(
                                                                                        Counterparty))
        self.counterparty_dynamic_attr_number = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                    name="Counterparty Num",
                                                                                    value_type=GenericAttributeType.NUMBER,
                                                                                    content_type=ContentType.objects.get_for_model(
                                                                                        Counterparty)
                                                                                    )
        self.counterparty_dynamic_attr_date = GenericAttributeType.objects.create(master_user=self.master_user,
                                                                                  name="Counterparty Date",
                                                                                  value_type=GenericAttributeType.DATE,
                                                                                  content_type=ContentType.objects.get_for_model(
                                                                                      Counterparty))

    def create_portfolio_scheme(self):
        scheme = CsvImportScheme.objects.create(name="Portfolio scheme",
                                       master_user=self.master_user,
                                       content_type=ContentType.objects.get_for_model(Portfolio))

        CsvField.objects.create(column=0, name="name", scheme=scheme)
        CsvField.objects.create(column=1, name="short_name", scheme=scheme)
        CsvField.objects.create(column=2, name="account", scheme=scheme)
        CsvField.objects.create(column=3, name="country", scheme=scheme)
        CsvField.objects.create(column=4, name="date", scheme=scheme)
        CsvField.objects.create(column=5, name="num", scheme=scheme)
        CsvField.objects.create(column=6, name="responsible", scheme=scheme)
        CsvField.objects.create(column=7, name="country_classifier", scheme=scheme)

        EntityField.objects.create(name="Name", expression="name", system_property_key="name", scheme=scheme)
        EntityField.objects.create(name="Short name", expression="short_name", system_property_key="short_name",
                                   scheme=scheme)
        EntityField.objects.create(name="Notes", expression="", system_property_key="notes", scheme=scheme)
        EntityField.objects.create(name="public name", expression="", system_property_key="public_name", scheme=scheme)
        EntityField.objects.create(name="User code", expression="name + '_us1'", system_property_key="user_code",
                                   scheme=scheme)
        EntityField.objects.create(name="Accounts", expression="account", system_property_key="accounts", scheme=scheme)
        EntityField.objects.create(name="Responsibles", expression="responsible", system_property_key="responsibles",
                                   scheme=scheme)
        EntityField.objects.create(name="Counterparties", expression="", system_property_key="counterparties",
                                   scheme=scheme)

        EntityField.objects.create(name="Test number", expression="num",
                                   dynamic_attribute_id=self.portfolio_dynamic_attr_number.id, scheme=scheme)
        EntityField.objects.create(name="Test Date", expression="date",
                                   dynamic_attribute_id=self.portfolio_dynamic_attr_date.id, scheme=scheme)
        EntityField.objects.create(name="Country", expression="country",
                                   dynamic_attribute_id=self.portfolio_dynamic_attr_string.id, scheme=scheme)
        EntityField.objects.create(name="Country (Classifier)", expression="country_classifier",
                                   dynamic_attribute_id=self.portfolio_dynamic_attr_classifier.id, scheme=scheme)

        return CsvImportScheme.objects.get(pk=scheme.id)

    def create_account_scheme(self):
        scheme = CsvImportScheme.objects.create(name="Account scheme", master_user=self.master_user, content_type=ContentType.objects.get_for_model(Account))

        CsvField.objects.create(column=0, name="name", scheme=scheme)
        CsvField.objects.create(column=1, name="code", scheme=scheme)
        CsvField.objects.create(column=2, name="short", scheme=scheme)
        CsvField.objects.create(column=3, name="notes", scheme=scheme)
        CsvField.objects.create(column=4, name="Op_date", scheme=scheme)
        CsvField.objects.create(column=5, name="target", scheme=scheme)
        CsvField.objects.create(column=6, name="public_name", scheme=scheme)
        CsvField.objects.create(column=7, name="PIN", scheme=scheme)
        CsvField.objects.create(column=8, name="Pass", scheme=scheme)

        EntityField.objects.create(name="Name", expression="name", system_property_key="name", scheme=scheme)
        EntityField.objects.create(name="Short name", expression="short", system_property_key="short_name",
                                   scheme=scheme)
        EntityField.objects.create(name="Notes", expression="notes", system_property_key="notes", scheme=scheme)
        EntityField.objects.create(name="public name", expression="public_name", system_property_key="public_name",
                                   scheme=scheme)
        EntityField.objects.create(name="User code", expression="code", system_property_key="user_code", scheme=scheme)

        EntityField.objects.create(name="PIN", expression="PIN",
                                   dynamic_attribute_id=self.account_dynamic_attr_number.id, scheme=scheme)
        EntityField.objects.create(name="OP Date", expression="Op_date",
                                   dynamic_attribute_id=self.account_dynamic_attr_date.id, scheme=scheme)
        EntityField.objects.create(name="Password", expression="Pass",
                                   dynamic_attribute_id=self.account_dynamic_attr_string.id, scheme=scheme)

        return CsvImportScheme.objects.get(pk=scheme.id)

    def create_counterparty_scheme(self):
        scheme = CsvImportScheme.objects.create(name="Counterparty scheme",
                                       master_user=self.master_user,
                                       content_type=ContentType.objects.get_for_model(Counterparty))

        CsvField.objects.create(column=0, name="name", scheme=scheme)
        CsvField.objects.create(column=1, name="notes", scheme=scheme)
        CsvField.objects.create(column=2, name="user_code", scheme=scheme)
        CsvField.objects.create(column=3, name="portfolios", scheme=scheme)
        CsvField.objects.create(column=4, name="rating", scheme=scheme)

        EntityField.objects.create(name="Name", expression="name", system_property_key="name", scheme=scheme)
        EntityField.objects.create(name="Notes", expression="notes", system_property_key="notes", scheme=scheme)
        EntityField.objects.create(name="User code", expression="user_code", system_property_key="user_code",
                                   scheme=scheme)
        EntityField.objects.create(name="Portfolios", expression="portfolios", system_property_key="portfolios",
                                   scheme=scheme)

        EntityField.objects.create(name="Rating", expression="rating",
                                   dynamic_attribute_id=self.counterparty_dynamic_attr_string.id, scheme=scheme)

        return CsvImportScheme.objects.get(pk=scheme.id)

    def create_responsible_scheme(self):
        scheme = CsvImportScheme.objects.create(name="Responsible scheme",
                                       master_user=self.master_user,
                                       content_type=ContentType.objects.get_for_model(Responsible))

        CsvField.objects.create(column=0, name="name", scheme=scheme)
        CsvField.objects.create(column=1, name="notes", scheme=scheme)
        CsvField.objects.create(column=2, name="user_code", scheme=scheme)
        CsvField.objects.create(column=3, name="portfolios", scheme=scheme)
        CsvField.objects.create(column=4, name="rating", scheme=scheme)

        EntityField.objects.create(name="Name", expression="name", system_property_key="name", scheme=scheme)
        EntityField.objects.create(name="Notes", expression="notes", system_property_key="notes", scheme=scheme)
        EntityField.objects.create(name="User code", expression="user_code", system_property_key="user_code",
                                   scheme=scheme)
        EntityField.objects.create(name="Portfolios", expression="portfolios", system_property_key="portfolios",
                                   scheme=scheme)

        EntityField.objects.create(name="Rating", expression="rating",
                                   dynamic_attribute_id=self.responsible_dynamic_attr_string.id, scheme=scheme)

        return CsvImportScheme.objects.get(pk=scheme.id)

    def test_scheme_create(self):
        return self.create_portfolio_scheme()

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

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_date.id)
        invalid_field.expression = "format_date(date)"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_dynamic_attribute_number_expression_valid(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_number.id)
        invalid_field.expression = "float(num) * 0.23"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_dynamic_attribute_string_expression_valid(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_string.id)
        invalid_field.expression = "country + ' risk'"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_dynamic_attribute_date_expression_invalid(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_date.id)
        invalid_field.expression = "format_date(date, format='%m-%Y-%d')"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_dynamic_attribute_number_expression_invalid(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_number.id)
        invalid_field.expression = "num / 0"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_dynamic_attribute_number_expression_invalid2(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_number.id)
        invalid_field.expression = "country"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_dynamic_attribute_string_expression_invalid(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        invalid_field = EntityField.objects.get(scheme=self.scheme,
                                                dynamic_attribute_id=self.portfolio_dynamic_attr_string.id)
        invalid_field.expression = "country ////"
        invalid_field.save()

        self.scheme = CsvImportScheme.objects.get(pk=self.scheme.id)

        rows = TestData.correct_file_rows

        results, process_errors = viewset.process_csv_file(self.master_user, self.scheme, rows, error_handler)

        process_errors = viewset.import_results(self.scheme, error_handler, results, process_errors)

        # Incorrect Scheme and correct File produces 4 errors

        self.assertEqual(len(process_errors), 4)

    def test_case_portfolio_import(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.portfolio_test_data

        results, process_errors = viewset.process_csv_file(self.master_user, self.portfolio_scheme, rows, error_handler)

        process_errors = viewset.import_results(self.portfolio_scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_account_import(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.account_test_data

        results, process_errors = viewset.process_csv_file(self.master_user, self.account_scheme, rows, error_handler)

        process_errors = viewset.import_results(self.account_scheme, error_handler, results, process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_counterparty_import(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.counterparty_test_data

        results, process_errors = viewset.process_csv_file(self.master_user, self.counterparty_scheme, rows,
                                                           error_handler)

        process_errors = viewset.import_results(self.counterparty_scheme, error_handler, results, process_errors)

        print(process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)

    def test_case_responsible_import(self):
        viewset = CsvDataImportViewSet()

        error_handler = 'continue'

        rows = TestData.responsible_test_data

        results, process_errors = viewset.process_csv_file(self.master_user, self.counterparty_scheme, rows,
                                                           error_handler)

        process_errors = viewset.import_results(self.counterparty_scheme, error_handler, results, process_errors)

        print(process_errors)

        # Correct Scheme and correct File produces 0 errors

        self.assertEqual(len(process_errors), 0)
