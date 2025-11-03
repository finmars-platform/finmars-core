from calendar import monthrange
from datetime import datetime, timedelta

from django.test import SimpleTestCase


def validate_iso_date_format(date_str: str):
    """
    Checks if a date string is in ISO format (YYYY-MM-DD).

    Parameters:
    date_str (str): The date string to validate.

    Returns:
    tuple: A tuple containing the status ('success' or 'error'), an error message if applicable,
           and the parsed date as a datetime object if successful.
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return "success", None, date
    except (TypeError, ValueError) as e:
        return "error", f"date ({date_str}) must be string type ISO format: {e}", None


def adjust_date(date: datetime, comparison_date: datetime = None, adjustment_type: str = None) -> datetime:
    """
    Adjusts the date based on the given adjustment type.

    Parameters:
    date (datetime): The date to adjust.
    comparison_date (datetime): The date to compare with.
    adjustment_type (str): Type of adjustment ('forward', 'backward', 'business_day_forward', 'business_day_back').

    Returns:
    datetime: The adjusted date.
    """
    if adjustment_type == "forward" and comparison_date:
        return max(date, comparison_date)
    elif adjustment_type == "backward" and comparison_date:
        return min(date, comparison_date)
    elif adjustment_type == "business_day_forward":
        if date.weekday() == 5:  # Saturday
            date += timedelta(days=2)
        elif date.weekday() == 6:  # Sunday
            date += timedelta(days=1)
    elif adjustment_type == "business_day_back":
        if date.weekday() == 5:  # Saturday
            date -= timedelta(days=1)
        elif date.weekday() == 6:  # Sunday
            date -= timedelta(days=2)
    return date


def adjust_dates(
    start_date: datetime,
    end_date: datetime,
    if_date_adjust_to_user_range: bool,
    if_use_business_day: bool,
    user_start_date: datetime = None,
    user_end_date: datetime = None,
) -> tuple:
    """
    Adjusts the start and end dates based on user range and business day flags.

    Parameters:
    start_date (datetime): The start date.
    end_date (datetime): The end date.
    if_date_adjust_to_user_range (bool): Whether to adjust based on user range.
    if_use_business_day (bool): Whether to adjust to the nearest business day.
    user_start_date (datetime): The user-defined start date.
    user_end_date (datetime): The user-defined end date.

    Returns:
    tuple: The adjusted start and end dates.
    """
    if if_date_adjust_to_user_range:
        start_date = adjust_date(start_date, user_start_date, "forward")
        end_date = adjust_date(end_date, user_end_date, "backward")

    if if_use_business_day:
        start_date = adjust_date(start_date, adjustment_type="business_day_forward")
        end_date = adjust_date(end_date, adjustment_type="business_day_back")

    return start_date, end_date


def get_daily_range(
    current_date: datetime, date_to: datetime, if_date_adjust_to_user_range: bool, if_use_business_day: bool
):
    current_date, _ = adjust_dates(
        current_date, date_to, if_date_adjust_to_user_range, if_use_business_day, current_date, date_to
    )
    next_date = current_date + timedelta(days=1)
    return (
        current_date.strftime("%Y-%m-%d"),
        current_date.strftime("%Y-%m-%d"),
    ), next_date


def get_weekly_range(
    current_date: datetime, date_to: datetime, if_date_adjust_to_user_range: bool, if_use_business_day: bool
):
    week_start = current_date - timedelta(days=current_date.weekday())
    week_end = week_start + timedelta(days=6)
    next_date = week_end + timedelta(days=1)

    week_start, week_end = adjust_dates(
        week_start, week_end, if_date_adjust_to_user_range, if_use_business_day, current_date, date_to
    )

    return (week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d")), next_date


def get_monthly_range(
    current_date: datetime, date_to: datetime, if_date_adjust_to_user_range: bool, if_use_business_day: bool
):
    _, last_day = monthrange(current_date.year, current_date.month)
    month_start = current_date.replace(day=1)
    month_end = current_date.replace(day=last_day)
    next_month_start = (month_end + timedelta(days=1)).replace(day=1)

    month_start, month_end = adjust_dates(
        month_start, month_end, if_date_adjust_to_user_range, if_use_business_day, current_date, date_to
    )

    return (
        month_start.strftime("%Y-%m-%d"),
        month_end.strftime("%Y-%m-%d"),
    ), next_month_start


def get_quarterly_range(
    current_date: datetime, date_to: datetime, if_date_adjust_to_user_range: bool, if_use_business_day: bool
):
    quarter_start_month = (current_date.month - 1) // 3 * 3 + 1
    quarter_start = datetime(current_date.year, quarter_start_month, 1)
    if quarter_start_month == 1:
        quarter_end = datetime(current_date.year, 3, 31)
    elif quarter_start_month == 4:
        quarter_end = datetime(current_date.year, 6, 30)
    elif quarter_start_month == 7:
        quarter_end = datetime(current_date.year, 9, 30)
    elif quarter_start_month == 10:
        quarter_end = datetime(current_date.year, 12, 31)
    else:
        raise ValueError("Invalid quarter start month")

    next_quarter_start = (quarter_end + timedelta(days=1)).replace(day=1)

    quarter_start, quarter_end = adjust_dates(
        quarter_start, quarter_end, if_date_adjust_to_user_range, if_use_business_day, current_date, date_to
    )

    return (
        quarter_start.strftime("%Y-%m-%d"),
        quarter_end.strftime("%Y-%m-%d"),
    ), next_quarter_start


def get_half_year_range(
    current_date: datetime, date_to: datetime, if_date_adjust_to_user_range: bool, if_use_business_day: bool
):
    if current_date.month <= 6:
        half_year_start = datetime(current_date.year, 1, 1)
        half_year_end = datetime(current_date.year, 6, 30)
    else:
        half_year_start = datetime(current_date.year, 7, 1)
        half_year_end = datetime(current_date.year, 12, 31)
    next_half_year_start = (half_year_end + timedelta(days=1)).replace(day=1)

    half_year_start, half_year_end = adjust_dates(
        half_year_start, half_year_end, if_date_adjust_to_user_range, if_use_business_day, current_date, date_to
    )

    return (
        half_year_start.strftime("%Y-%m-%d"),
        half_year_end.strftime("%Y-%m-%d"),
    ), next_half_year_start


def get_yearly_range(
    current_date: datetime, date_to: datetime, if_date_adjust_to_user_range: bool, if_use_business_day: bool
):
    year_start = datetime(current_date.year, 1, 1)
    year_end = datetime(current_date.year, 12, 31)
    next_year_start = (year_end + timedelta(days=1)).replace(day=1)

    year_start, year_end = adjust_dates(
        year_start, year_end, if_date_adjust_to_user_range, if_use_business_day, current_date, date_to
    )

    return (
        year_start.strftime("%Y-%m-%d"),
        year_end.strftime("%Y-%m-%d"),
    ), next_year_start


def get_custom_range(date_from: datetime, date_to: datetime):
    return [(date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))]


def split_date_range_list(  # noqa: PLR0911
    date_from_str: str,
    date_to_str: str,
    period_type: str = "daily",
    if_date_adjust_to_user_range: bool = False,
    if_use_business_day: bool = False,
) -> tuple:
    """
    Splits a given date range into multiple non-overlapping periods based on the specified period type.
    Each period will be fully contained within the date_from and date_to range
    if if_date_adjust_to_user_range = True.
    If if_date_adjust_to_user_range = False, the overall date range may be broadened to
    the actual start and end dates of the selected period_type.

    Parameters:
    date_from_str (str): Start date in 'YYYY-MM-DD' format.
    date_to_str (str): End date in 'YYYY-MM-DD' format.
    period_type (str): The type of period for splitting the date range. Options are:
                       'daily', 'weekly', 'monthly', 'quarterly', 'half-year', 'yearly', 'custom'.
    if_date_adjust_to_user_range (bool): Whether to adjust the period start/end dates to ensure
                                         they are within the user-specified date range.
    if_use_business_day (bool): Whether to adjust the start/end dates to the nearest business day.

    Returns:
    tuple: A tuple containing the status ('success' or 'error'), an error message if applicable,
           and a list of date ranges.
    """
    if not date_from_str or not date_to_str:
        return "error", "Both date_from_str and date_to_str must be provided.", None

    status_date_from, err_msg_date_from, date_from = validate_iso_date_format(date_from_str)
    status_date_to, err_msg_date_to, date_to = validate_iso_date_format(date_to_str)
    if status_date_from == "error" or status_date_to == "error":
        err_msg = "; ".join(filter(None, [err_msg_date_from, err_msg_date_to]))
        return "error", err_msg, None

    if if_use_business_day:
        date_from_adj = adjust_date(date_from, adjustment_type="business_day_forward")
        date_to_adj = adjust_date(date_to, adjustment_type="business_day_back")

        if date_from_adj > date_to_adj:
            return (
                "error",
                f"if_use_business_day=True but date range is fully in weekend: "
                f"date_from ({date_from_str}), date_to ({date_to_str})",
                None,
            )

        date_from, date_to = date_from_adj, date_to_adj

    if date_to < date_from:
        return "error", f"date_to ({date_to}) < date_from ({date_from})", None

    if date_from == date_to:
        if period_type in {"daily", "custom"}:
            return (
                "success",
                None,
                [(date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))],
            )
        else:
            return (
                "error",
                f"date_to ({date_to}) == date_from ({date_from}) for non-daily or "
                f"non-custom period_type ({period_type})",
                None,
            )

    period_mapping = {
        "daily": get_daily_range,
        "weekly": get_weekly_range,
        "monthly": get_monthly_range,
        "quarterly": get_quarterly_range,
        "half-year": get_half_year_range,
        "yearly": get_yearly_range,
        "custom": get_custom_range,
    }

    if period_type not in period_mapping:
        return (
            "error",
            f"period_type ({period_type}) must be from: {list(period_mapping.keys())}.",
            None,
        )

    if period_type == "custom":
        return "success", None, period_mapping[period_type](date_from, date_to)

    date_ranges = []
    current_date = date_from
    while current_date <= date_to:
        date_range, current_date = period_mapping[period_type](
            current_date, date_to, if_date_adjust_to_user_range, if_use_business_day
        )
        date_ranges.append(date_range)

    return "success", None, date_ranges


class TestSplitDateRangeList(SimpleTestCase):
    maxDiff = None

    def _run_case(self, case):
        status, msg, res = split_date_range_list(
            case.get("date_from_str"),
            case.get("date_to_str"),
            case.get("period_type"),
            case.get("if_date_adjust_to_user_range"),
            case.get("if_use_business_day"),
        )
        return status, msg, res

    def test_error_when_no_date_to(self):
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        for i, period_type in enumerate(period_types):
            for if_date_adjust_to_user_range in (False, True):
                for if_use_business_day in (False, True):
                    case = {
                        "num": i,
                        "date_from_str": "2024-01-13",
                        "date_to_str": None,
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    with self.subTest(case=case):
                        status, msg, res = self._run_case(case)
                        self.assertEqual(status, "error")
                        self.assertIsNone(res)
                        self.assertIn("must be provided", msg)

    def test_error_when_no_date_from(self):
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        for i, period_type in enumerate(period_types):
            for if_date_adjust_to_user_range in (False, True):
                for if_use_business_day in (False, True):
                    case = {
                        "num": i,
                        "date_from_str": None,
                        "date_to_str": "2024-01-13",
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    with self.subTest(case=case):
                        status, msg, res = self._run_case(case)
                        self.assertEqual(status, "error")
                        self.assertIsNone(res)
                        self.assertIn("must be provided", msg)

    def test_error_when_invalid_period_type(self):
        for if_date_adjust_to_user_range in (False, True):
            for if_use_business_day in (False, True):
                case = {
                    "num": 0,
                    "date_from_str": "2024-01-13",
                    "date_to_str": "2024-01-15",
                    "period_type": None,
                    "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                    "if_use_business_day": if_use_business_day,
                    "res": None,
                }
                with self.subTest(case=case):
                    status, msg, res = self._run_case(case)
                    self.assertEqual(status, "error")
                    self.assertIsNone(res)
                    self.assertIn("period_type", msg)

    def test_error_when_date_to_earlier(self):
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        for i, period_type in enumerate(period_types):
            for if_date_adjust_to_user_range in (False, True):
                for if_use_business_day in (False, True):
                    case = {
                        "num": i,
                        "date_from_str": "2024-01-13",
                        "date_to_str": "2024-01-12",
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    with self.subTest(case=case):
                        status, msg, res = self._run_case(case)
                        self.assertEqual(status, "error")
                        self.assertIsNone(res)
                        # self.assertIn("<", msg)

    def test_error_when_fully_in_weekend_business_day(self):
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        for i, period_type in enumerate(period_types):
            for if_date_adjust_to_user_range in (False, True):
                case = {
                    "num": i,
                    "date_from_str": "2024-01-13",  # Saturday
                    "date_to_str": "2024-01-13",  # Saturday
                    "period_type": period_type,
                    "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                    "if_use_business_day": True,
                    "res": None,
                }
                with self.subTest(case=case):
                    status, msg, res = self._run_case(case)
                    self.assertEqual(status, "error")
                    self.assertIsNone(res)
                    self.assertIn("fully in weekend", msg)

    def test_daily_examples(self):
        # A couple of representative success cases from the standalone script
        cases = [
            {
                "date_from_str": "2024-08-18",
                "date_to_str": "2024-08-24",
                "period_type": "daily",
                "if_date_adjust_to_user_range": False,
                "if_use_business_day": False,
                "res": [
                    ("2024-08-18", "2024-08-18"),
                    ("2024-08-19", "2024-08-19"),
                    ("2024-08-20", "2024-08-20"),
                    ("2024-08-21", "2024-08-21"),
                    ("2024-08-22", "2024-08-22"),
                    ("2024-08-23", "2024-08-23"),
                    ("2024-08-24", "2024-08-24"),
                ],
            },
            {
                "date_from_str": "2024-08-18",
                "date_to_str": "2024-08-24",
                "period_type": "daily",
                "if_date_adjust_to_user_range": False,
                "if_use_business_day": True,
                "res": [
                    ("2024-08-19", "2024-08-19"),
                    ("2024-08-20", "2024-08-20"),
                    ("2024-08-21", "2024-08-21"),
                    ("2024-08-22", "2024-08-22"),
                    ("2024-08-23", "2024-08-23"),
                ],
            },
        ]
        for case in cases:
            with self.subTest(case=case):
                status, msg, res = self._run_case(case)
                self.assertEqual(status, "success")
                self.assertIsNone(msg)
                self.assertEqual(res, case["res"])


if __name__ == "__main__":

    def split_date_range_list_test_check(test_cases: list[dict]):
        for test_case in test_cases:
            num = test_case["num"]
            print(f"test case # {num}")
            date_from_str = test_case.get("date_from_str")
            date_to_str = test_case.get("date_to_str")
            period_type = test_case.get("period_type")
            if_date_adjust_to_user_range = test_case.get("if_date_adjust_to_user_range")
            if_use_business_day = test_case.get("if_use_business_day")
            _, _, res = split_date_range_list(
                date_from_str,
                date_to_str,
                period_type,
                if_date_adjust_to_user_range,
                if_use_business_day,
            )
            # Removed incorrect reversal; cause results are already in ascending order
            # if isinstance(res, list):
            #     res = res[::-1]
            assert res == test_case["res"], (
                f"\ntest_case num {num}\ntest_case date_from_str: {date_from_str}\n"
                f"test_case date_to_str: {date_to_str}\ntest_case period_type: {period_type}\n"
                f"test_case if_date_adjust_to_user_range: {if_date_adjust_to_user_range}\n"
                f"test_case if_use_business_day: {if_use_business_day}\nres: {res}\n"
                f"test_case res: {test_case['res']}"
            )

    print("starting split_date_range_list_tests_generate_if_no_date_to")

    def split_date_range_list_tests_generate_if_no_date_to():
        cases_if_date_to_earlier = []
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        if_date_adjust_to_user_range_vals = [False, True]
        if_use_business_day_vals = [False, True]
        num = 0
        for period_type in period_types:
            for if_date_adjust_to_user_range in if_date_adjust_to_user_range_vals:
                for if_use_business_day in if_use_business_day_vals:
                    case = {
                        "num": num,
                        "date_from_str": "2024-01-10",
                        # "date_to_str": "2024-01-12",
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    cases_if_date_to_earlier.append(case)
                    num += 1
        return cases_if_date_to_earlier

    split_date_range_list_test_check(split_date_range_list_tests_generate_if_no_date_to())

    print("starting split_date_range_list_tests_generate_if_no_date_from")

    def split_date_range_list_tests_generate_if_no_date_from():
        cases_if_date_to_earlier = []
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        if_date_adjust_to_user_range_vals = [False, True]
        if_use_business_day_vals = [False, True]
        num = 0
        for period_type in period_types:
            for if_date_adjust_to_user_range in if_date_adjust_to_user_range_vals:
                for if_use_business_day in if_use_business_day_vals:
                    case = {
                        "num": num,
                        # "date_from_str": "2024-01-10",
                        "date_to_str": "2024-01-12",
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    cases_if_date_to_earlier.append(case)
                    num += 1
        return cases_if_date_to_earlier

    split_date_range_list_test_check(split_date_range_list_tests_generate_if_no_date_from())

    print("starting split_date_range_list_tests_generate_if_no_period_type")

    def split_date_range_list_tests_generate_if_no_period_type():
        cases_if_date_to_earlier = []
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        if_date_adjust_to_user_range_vals = [False, True]
        if_use_business_day_vals = [False, True]
        num = 0
        for _ in period_types:
            for if_date_adjust_to_user_range in if_date_adjust_to_user_range_vals:
                for if_use_business_day in if_use_business_day_vals:
                    case = {
                        "num": num,
                        "date_from_str": "2024-01-10",
                        "date_to_str": "2024-01-12",
                        # "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    cases_if_date_to_earlier.append(case)
                    num += 1
        return cases_if_date_to_earlier

    split_date_range_list_test_check(split_date_range_list_tests_generate_if_no_period_type())

    print("starting split_date_range_list_tests_generate_if_date_to_earlier")

    def split_date_range_list_tests_generate_if_date_to_earlier():
        cases_if_date_to_earlier = []
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        if_date_adjust_to_user_range_vals = [False, True]
        if_use_business_day_vals = [False, True]
        num = 0
        for period_type in period_types:
            for if_date_adjust_to_user_range in if_date_adjust_to_user_range_vals:
                for if_use_business_day in if_use_business_day_vals:
                    case = {
                        "num": num,
                        "date_from_str": "2024-01-13",
                        "date_to_str": "2024-01-12",
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    cases_if_date_to_earlier.append(case)
                    num += 1
        return cases_if_date_to_earlier

    split_date_range_list_test_check(split_date_range_list_tests_generate_if_date_to_earlier())

    print("starting split_date_range_list_tests_generate_if_fully_in_weekend_business_day")

    def split_date_range_list_tests_generate_if_fully_in_weekend_business_day():
        cases_if_date_to_earlier = []
        period_types = [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "half-year",
            "yearly",
            "custom",
        ]
        if_date_adjust_to_user_range_vals = [False, True]
        # if_use_business_day_vals  = [False, True]
        if_use_business_day_vals = [True]
        num = 0
        for period_type in period_types:
            for if_date_adjust_to_user_range in if_date_adjust_to_user_range_vals:
                for if_use_business_day in if_use_business_day_vals:
                    case = {
                        "num": num,
                        "date_from_str": "2024-01-13",
                        "date_to_str": "2024-01-13",
                        "period_type": period_type,
                        "if_date_adjust_to_user_range": if_date_adjust_to_user_range,
                        "if_use_business_day": if_use_business_day,
                        "res": None,
                    }
                    cases_if_date_to_earlier.append(case)
                    num += 1
        return cases_if_date_to_earlier

    split_date_range_list_test_check(split_date_range_list_tests_generate_if_fully_in_weekend_business_day())

    print("starting daily_test_cases")
    daily_test_cases = [
        {
            "num": 0,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-24",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
                ("2024-08-24", "2024-08-24"),
            ],
        },
        {
            "num": 1,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-24",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
                ("2024-08-24", "2024-08-24"),
            ],
        },
        {
            "num": 2,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-24",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
            ],
        },
        {
            "num": 3,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-24",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
            ],
        },
        {
            "num": 4,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-23",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
            ],
        },
        {
            "num": 5,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-23",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
            ],
        },
        {
            "num": 6,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-23",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
            ],
        },
        {
            "num": 7,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-23",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
            ],
        },
        {
            "num": 8,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-31",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
                ("2024-08-24", "2024-08-24"),
                ("2024-08-25", "2024-08-25"),
                ("2024-08-26", "2024-08-26"),
                ("2024-08-27", "2024-08-27"),
                ("2024-08-28", "2024-08-28"),
                ("2024-08-29", "2024-08-29"),
                ("2024-08-30", "2024-08-30"),
                ("2024-08-31", "2024-08-31"),
            ],
        },
        {
            "num": 9,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-31",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
                ("2024-08-24", "2024-08-24"),
                ("2024-08-25", "2024-08-25"),
                ("2024-08-26", "2024-08-26"),
                ("2024-08-27", "2024-08-27"),
                ("2024-08-28", "2024-08-28"),
                ("2024-08-29", "2024-08-29"),
                ("2024-08-30", "2024-08-30"),
                ("2024-08-31", "2024-08-31"),
            ],
        },
        {
            "num": 10,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-31",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                # ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
                # ("2024-08-24", "2024-08-24"),
                # ("2024-08-25", "2024-08-25"),
                ("2024-08-26", "2024-08-26"),
                ("2024-08-27", "2024-08-27"),
                ("2024-08-28", "2024-08-28"),
                ("2024-08-29", "2024-08-29"),
                ("2024-08-30", "2024-08-30"),
                # ("2024-08-31", "2024-08-31"),
            ],
        },
        {
            "num": 11,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-31",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                # ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-19"),
                ("2024-08-20", "2024-08-20"),
                ("2024-08-21", "2024-08-21"),
                ("2024-08-22", "2024-08-22"),
                ("2024-08-23", "2024-08-23"),
                # ("2024-08-24", "2024-08-24"),
                # ("2024-08-25", "2024-08-25"),
                ("2024-08-26", "2024-08-26"),
                ("2024-08-27", "2024-08-27"),
                ("2024-08-28", "2024-08-28"),
                ("2024-08-29", "2024-08-29"),
                ("2024-08-30", "2024-08-30"),
                # ("2024-08-31", "2024-08-31"),
            ],
        },
        {
            "num": 12,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-19",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-19", "2024-08-19"),
            ],
        },
        {
            "num": 13,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-19",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-08-19", "2024-08-19"),
            ],
        },
        {
            "num": 14,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-19",
            "period_type": "daily",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-19"),
            ],
        },
        {
            "num": 15,
            "date_from_str": "2024-08-19",
            "date_to_str": "2024-08-19",
            "period_type": "daily",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-19"),
            ],
        },
    ]
    split_date_range_list_test_check(daily_test_cases)

    print("starting weekly_test_cases")
    weekly_test_cases = [
        {
            "num": 0,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-25",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-12", "2024-08-18"),
                ("2024-08-19", "2024-08-25"),
            ],
        },
        {
            "num": 1,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-25",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-08-18", "2024-08-18"),
                ("2024-08-19", "2024-08-25"),
            ],
        },
        {
            "num": 2,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-25",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-08-19", "2024-08-23"),
            ],
        },
        {
            "num": 3,
            "date_from_str": "2024-08-18",
            "date_to_str": "2024-08-25",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                # ("2024-08-12", "2024-08-16"),
                ("2024-08-19", "2024-08-23"),
            ],
        },
        {
            "num": 4,
            "date_from_str": "2024-08-16",
            "date_to_str": "2024-08-25",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-12", "2024-08-18"),
                ("2024-08-19", "2024-08-25"),
            ],
        },
        {
            "num": 5,
            "date_from_str": "2024-08-16",
            "date_to_str": "2024-08-24",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-08-12", "2024-08-18"),
                ("2024-08-19", "2024-08-25"),
            ],
        },
        {
            "num": 6,
            "date_from_str": "2024-08-16",
            "date_to_str": "2024-08-24",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-08-16", "2024-08-18"),
                ("2024-08-19", "2024-08-24"),
            ],
        },
        {
            "num": 7,
            "date_from_str": "2024-08-16",
            "date_to_str": "2024-08-24",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-08-12", "2024-08-16"),
                ("2024-08-19", "2024-08-23"),
            ],
        },
        {
            "num": 8,
            "date_from_str": "2024-08-16",
            "date_to_str": "2024-08-24",
            "period_type": "weekly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-08-16", "2024-08-16"),
                ("2024-08-19", "2024-08-23"),
            ],
        },
    ]
    split_date_range_list_test_check(weekly_test_cases)

    print("starting monthly_test_cases")
    monthly_test_cases = [
        {
            "num": 0,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "monthly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-31"),
            ],
        },
        {
            "num": 1,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "monthly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-02-02", "2024-02-29"),
                ("2024-03-01", "2024-03-27"),
            ],
        },
        {
            "num": 2,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "monthly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-29"),
            ],
        },
        {
            "num": 3,
            "date_from_str": "2024-02-03",
            "date_to_str": "2024-03-30",
            "period_type": "monthly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-02-01", "2024-02-29"),
                ("2024-03-01", "2024-03-29"),
            ],
        },
        {
            "num": 4,
            "date_from_str": "2024-02-03",
            "date_to_str": "2024-03-30",
            "period_type": "monthly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-02-05", "2024-02-29"),
                ("2024-03-01", "2024-03-29"),
            ],
        },
    ]
    split_date_range_list_test_check(monthly_test_cases)

    print("starting quarterly_test_cases")
    quarterly_test_cases = [
        {
            "num": 0,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-01-01", "2024-03-31"),
            ],
        },
        {
            "num": 1,
            "date_from_str": "2023-11-15",
            "date_to_str": "2024-05-15",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2023-10-01", "2023-12-31"),
                ("2024-01-01", "2024-03-31"),
                ("2024-04-01", "2024-06-30"),
            ],
        },
        {
            "num": 2,
            "date_from_str": "2023-11-15",
            "date_to_str": "2024-05-15",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2023-11-15", "2023-12-31"),
                ("2024-01-01", "2024-03-31"),
                ("2024-04-01", "2024-05-15"),
            ],
        },
        {
            "num": 3,
            "date_from_str": "2024-04-10",
            "date_to_str": "2024-10-05",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-04-10", "2024-06-30"),
                ("2024-07-01", "2024-09-30"),
                ("2024-10-01", "2024-10-05"),
            ],
        },
        {
            "num": 4,
            "date_from_str": "2024-01-02",
            "date_to_str": "2024-09-28",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2024-01-01", "2024-03-29"),
                ("2024-04-01", "2024-06-28"),
                ("2024-07-01", "2024-09-30"),
            ],
        },
        {
            "num": 5,
            "date_from_str": "2024-01-02",
            "date_to_str": "2024-09-28",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-01-02", "2024-03-29"),
                ("2024-04-01", "2024-06-28"),
                ("2024-07-01", "2024-09-27"),
            ],
        },
        {
            "num": 5,
            "date_from_str": "2024-01-01",
            "date_to_str": "2024-03-31",
            "period_type": "quarterly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-01-01", "2024-03-31"),
            ],
        },
    ]
    split_date_range_list_test_check(quarterly_test_cases)

    print("starting half_year_test_cases")
    half_year_test_cases = [
        {
            "num": 0,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-01-01", "2024-06-30"),
            ],
        },
        {
            "num": 1,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-02-02", "2024-03-27"),
            ],
        },
        {
            "num": 2,
            "date_from_str": "2024-02-03",
            "date_to_str": "2024-03-30",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-02-05", "2024-03-29"),
            ],
        },
        {
            "num": 3,
            "date_from_str": "2024-07-15",
            "date_to_str": "2024-12-25",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-07-01", "2024-12-31"),
            ],
        },
        {
            "num": 4,
            "date_from_str": "2024-01-15",
            "date_to_str": "2024-12-15",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2024-01-01", "2024-06-30"),
                ("2024-07-01", "2024-12-31"),
            ],
        },
        {
            "num": 5,
            "date_from_str": "2024-02-02",
            "date_to_str": "2024-06-29",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2024-02-02", "2024-06-29"),
            ],
        },
        {
            "num": 6,
            "date_from_str": "2024-07-01",
            "date_to_str": "2024-12-31",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-07-01", "2024-12-31"),
            ],
        },
        {
            "num": 7,
            "date_from_str": "2024-01-01",
            "date_to_str": "2024-06-30",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2024-01-01", "2024-06-28"),
            ],
        },
        {
            "num": 8,
            "date_from_str": "2023-01-01",
            "date_to_str": "2024-06-30",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2023-01-01", "2023-06-30"),
                ("2023-07-01", "2023-12-31"),
                ("2024-01-01", "2024-06-30"),
            ],
        },
        {
            "num": 9,
            "date_from_str": "2023-01-01",
            "date_to_str": "2024-06-29",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2023-01-01", "2023-06-30"),
                ("2023-07-01", "2023-12-31"),
                ("2024-01-01", "2024-06-29"),
            ],
        },
        {
            "num": 10,
            "date_from_str": "2023-01-01",
            "date_to_str": "2024-06-29",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2023-01-02", "2023-06-30"),
                ("2023-07-03", "2023-12-29"),
                ("2024-01-01", "2024-06-28"),
            ],
        },
        {
            "num": 11,
            "date_from_str": "2023-01-01",
            "date_to_str": "2024-06-29",
            "period_type": "half-year",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2023-01-02", "2023-06-30"),
                ("2023-07-03", "2023-12-29"),
                ("2024-01-01", "2024-06-28"),
            ],
        },
    ]
    split_date_range_list_test_check(half_year_test_cases)

    print("starting yearly_test_cases")
    yearly_test_cases = [
        {
            "num": 0,
            "date_from_str": "2022-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2022-01-01", "2022-12-31"),
                ("2023-01-01", "2023-12-31"),
                ("2024-01-01", "2024-12-31"),
            ],
        },
        {
            "num": 1,
            "date_from_str": "2022-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2022-02-02", "2022-12-31"),
                ("2023-01-01", "2023-12-31"),
                ("2024-01-01", "2024-03-27"),
            ],
        },
        {
            "num": 2,
            "date_from_str": "2022-02-02",
            "date_to_str": "2024-03-27",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2022-02-02", "2022-12-30"),
                ("2023-01-02", "2023-12-29"),
                ("2024-01-01", "2024-03-27"),
            ],
        },
        {
            "num": 3,
            "date_from_str": "2022-12-31",
            "date_to_str": "2024-01-01",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": True,
            "res": [
                ("2023-01-02", "2023-12-29"),
                ("2024-01-01", "2024-12-31"),
            ],
        },
        {
            "num": 4,
            "date_from_str": "2022-12-31",
            "date_to_str": "2024-01-01",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": True,
            "res": [
                ("2023-01-02", "2023-12-29"),
                ("2024-01-01", "2024-01-01"),
            ],
        },
        {
            "num": 5,
            "date_from_str": "2022-12-31",
            "date_to_str": "2024-01-01",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": False,
            "if_use_business_day": False,
            "res": [
                ("2022-01-01", "2022-12-31"),
                ("2023-01-01", "2023-12-31"),
                ("2024-01-01", "2024-12-31"),
            ],
        },
        {
            "num": 6,
            "date_from_str": "2022-12-31",
            "date_to_str": "2024-01-01",
            "period_type": "yearly",
            "if_date_adjust_to_user_range": True,
            "if_use_business_day": False,
            "res": [
                ("2022-12-31", "2022-12-31"),
                ("2023-01-01", "2023-12-31"),
                ("2024-01-01", "2024-01-01"),
            ],
        },
    ]
    split_date_range_list_test_check(yearly_test_cases)

    print("test_cases passed")
