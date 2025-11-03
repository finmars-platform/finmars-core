import json
from datetime import datetime

from django.test import SimpleTestCase

from poms.common.utils import calculate_period_date


def test_func(func, test_cases, verbose=True):
    """
    Test a function with multiple test cases.

    :param func: The function to be tested.
    :param test_cases: A list of test cases, each a dictionary containing:
        - 'test_num': the test case number,
        - 'expected_res': the expected result of the test case,
        - other parameters required by the function being tested.
    :param verbose: If True, will print details of each test case; otherwise, will only print pass/fail messages.
    """

    def datetime_converter(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # Converts datetime to a string in ISO 8601 format
        raise TypeError("Type not serializable")

    print(f"{func.__name__} test is starting ...")

    for test_case in test_cases:
        test_num = test_case["test_num"]
        expected_res = test_case["expected_res"]

        # Prepare arguments for the function by excluding 'test_num' and 'expected_res'
        needed_test_fields = {key: val for key, val in test_case.items() if key not in ["test_num", "expected_res"]}

        # Call the function with unpacked arguments
        res = func(**needed_test_fields)

        # Error message with all details
        err_msg = (
            f"test #{test_num} - failed\n"
            f"Test case:\n"
            f"{json.dumps(test_case, indent=4, default=datetime_converter)}\n"
            f"{{\n"
            f"    Exp result: {json.dumps(expected_res, default=datetime_converter)}\n"
            f"    Act result: {json.dumps(res, default=datetime_converter)}\n"
            f"}}"
        )

        try:
            assert res == expected_res, err_msg
            if verbose:
                print(f"test #{test_num} - passed")
        except AssertionError as e:
            if verbose:
                print(e)
            else:
                print(f"test #{test_num} - failed")

    print(f"{func.__name__} test is finished.\n")


def calc_period_date_test():
    test_cases = [
        {
            "test_num": 0,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "D",
            "shift": 0,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 1,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "D",
            "shift": 0,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 2,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "D",
            "shift": 0,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 6).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 3,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "D",
            "shift": 0,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 9).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 4,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "D",
            "shift": 1,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 9).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 5,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "D",
            "shift": -1,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 6).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 6,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 0,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 2).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 7,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 0,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 8).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 8,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 0,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 2).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 9,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 0,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 6).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 10,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": -7,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 7, 15).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 11,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": -7,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 7, 21).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 12,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": -7,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 7, 15).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 13,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": -7,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2024, 7, 19).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 14,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 52,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2025, 9, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 15,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 52,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2025, 9, 7).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 16,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 52,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2025, 9, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 17,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "W",
            "shift": 52,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2025, 9, 5).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 18,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 0,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 19,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 0,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 20,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 0,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 2).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 21,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 0,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 22,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 25,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2026, 10, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 23,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 25,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2026, 10, 31).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 24,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 25,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2026, 10, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 25,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": 25,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2026, 10, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 26,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": -19,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2023, 2, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 27,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": -19,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2023, 2, 28).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 28,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": -19,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2023, 2, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 29,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "M",
            "shift": -19,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2023, 2, 28).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 30,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 0,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 7, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 31,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 0,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 9, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 32,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 0,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2024, 7, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 33,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 0,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2024, 9, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 34,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 10,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2027, 1, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 35,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 10,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2027, 3, 31).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 36,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 10,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2027, 1, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 37,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": 10,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2027, 3, 31).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 36,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": -10,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2022, 1, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 37,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": -10,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2022, 3, 31).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 38,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": -10,
            "start": True,
            "is_only_bday": True,
            "expected_res": datetime(2022, 1, 3).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 39,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "Q",
            "shift": -10,
            "start": False,
            "is_only_bday": True,
            "expected_res": datetime(2022, 3, 31).strftime("%Y-%m-%d"),
        },
        # Half-yearly (HY) tests derived from Sergey's hytd cases
        {
            "test_num": 40,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": 0,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 7, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 41,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": 0,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 12, 31).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 42,
            "input_date": datetime(2024, 2, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": 0,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2024, 1, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 43,
            "input_date": datetime(2024, 2, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": 0,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2024, 6, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 44,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": -3,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2023, 1, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 45,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": -3,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2023, 6, 30).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 46,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": 4,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2026, 7, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 47,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": 4,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2026, 12, 31).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 48,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": -8,
            "start": True,
            "is_only_bday": False,
            "expected_res": datetime(2020, 7, 1).strftime("%Y-%m-%d"),
        },
        {
            "test_num": 49,
            "input_date": datetime(2024, 9, 7).strftime("%Y-%m-%d"),
            "frequency": "HY",
            "shift": -8,
            "start": False,
            "is_only_bday": False,
            "expected_res": datetime(2020, 12, 31).strftime("%Y-%m-%d"),
        },
    ]
    test_func(calculate_period_date, test_cases)


class TestCalcPeriodTest(SimpleTestCase):
    maxDiff = None

    def test_calc_period_date(self):
        calc_period_date_test()
