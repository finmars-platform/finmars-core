import random
import string
from datetime import date, datetime, timedelta

from django.test import TestCase
from rest_framework.test import APIClient


class TestMetaClass(type):
    def __new__(mcs, name, bases, dct):
        # sourcery skip: class-method-first-arg-name
        for attr_name in list(dct.keys()):
            if hasattr(dct[attr_name], "test_cases"):
                cases = dct[attr_name].test_cases
                del dct[attr_name].test_cases
                hidden_name = f"__{attr_name}"
                mcs._move_method(dct, attr_name, hidden_name)

                for case in cases:
                    mcs._add_test_method(dct, attr_name, hidden_name, case[0], case[1:])

        return super(TestMetaClass, mcs).__new__(mcs, name, bases, dct)

    @classmethod
    def _move_method(mcs, dct, from_name, to_name):
        # sourcery skip: class-method-first-arg-name
        dct[to_name] = dct[from_name]
        dct[to_name].__name__ = str(to_name)
        del dct[from_name]

    @classmethod
    def _add_test_method(mcs, dct, orig_name, hidden_name, postfix, params):
        test_method_name = "{}__{}".format(orig_name, postfix)

        def test_method(self):
            return getattr(self, hidden_name)(*params)

        test_method.__name__ = test_method_name
        dct[test_method_name] = test_method


class BaseTestCase(TestCase, metaclass=TestMetaClass):
    client: APIClient = None
    patchers: list = []

    @classmethod
    def cases(cls, *cases):
        """
        Create a bunch of test methods using the case table and test code.
        Example. The following two pieces of code would behave identically:

        @BaseTestCase.cases(['name1', 1], ['name2', 2])
        def test_example(self, number):
            self.assertGreater(number, 0)

        def __test_example(self, number):
            self.assertGreater(number, 0)
        def test_example__name1(self):
            return self.__test_example(1)
        def test_example__name2(self):
            return self.__test_example(2)
        """

        def decorator(test_method):
            test_method.test_cases = cases
            return test_method

        return decorator

    @classmethod
    def random_int(cls, _min: int = 1, _max: int = 10000) -> int:
        return random.randint(_min, _max)

    @classmethod
    def random_string(cls, length: int = 10) -> str:
        return "".join(
            random.SystemRandom().choice(string.ascii_uppercase) for _ in range(length)
        )

    @classmethod
    def random_email(cls) -> str:
        return f"{cls.random_string(5)}@{cls.random_string(3)}.{cls.random_string(2)}"

    @classmethod
    def random_future_date(cls, interval=30) -> date:
        days = cls.random_int(1, interval)
        return datetime.now().date() + timedelta(days=days)

    @classmethod
    def random_choice(cls, choices: list):
        return random.choice(choices)

    def init_test_case(self):
        self.client = APIClient()


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code
        self.content = str(json_data)

    def json(self):
        return self.json_data


def show_all_urls():
    """
    Print all urls in the project
    """
    from django.urls import get_resolver

    def print_urls(resolver, prefix="/"):
        for url_pattern in resolver.url_patterns:
            if hasattr(url_pattern, "url_patterns"):
                print_urls(
                    url_pattern,
                    prefix=f"{prefix}{url_pattern.pattern.regex.pattern}",
                )
            else:
                print(f"{prefix}{url_pattern.pattern.regex.pattern}")

    print("------------------------------------------------")
    django_resolver = get_resolver(None)
    print_urls(django_resolver)
    print("------------------------------------------------")
