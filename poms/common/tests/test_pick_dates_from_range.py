import datetime

from django.test import SimpleTestCase

from poms.common.utils import pick_dates_from_range


class TestPickDatesFromRange(SimpleTestCase):
    def test_pick_dates_from_range(self):
        test_cases = [
            (datetime.date(2024, 8, 3), datetime.date(2024, 10, 13), "M", True, True),
            (datetime.date(2024, 8, 3), datetime.date(2024, 10, 13), "M", False, False),
            (datetime.date(2024, 8, 31), datetime.date(2024, 10, 1), "W", True, True),
            (datetime.date(2024, 8, 31), datetime.date(2024, 10, 1), "W", False, True),
            (datetime.date(2022, 12, 15), datetime.date(2024, 12, 3), "Y", False, True),
            (
                datetime.date(2022, 12, 15),
                datetime.date(2024, 12, 14),
                "Y",
                True,
                False,
            ),
            (datetime.date(2024, 9, 1), datetime.date(2024, 9, 5), "D", True, False),
            (datetime.date(2024, 1, 1), datetime.date(2024, 5, 1), "Q", False, True),
            (datetime.date(2023, 12, 15), datetime.date(2024, 4, 1), "Q", False, True),
            (datetime.date(2023, 12, 15), datetime.date(2024, 4, 1), "Q", False, False),
        ]

        expected = [
            ["2024-08-05", "2024-09-02", "2024-10-01"],
            ["2024-08-31", "2024-09-30", "2024-10-13"],
            ["2024-09-02", "2024-09-09", "2024-09-16", "2024-09-23"],
            ["2024-08-31", "2024-09-02", "2024-09-09", "2024-09-16", "2024-09-23"],
            ["2022-12-15", "2023-01-01", "2024-01-01"],
            ["2022-12-30", "2023-12-29", "2024-12-13"],
            ["2024-09-02", "2024-09-03", "2024-09-04", "2024-09-05"],
            ["2024-01-01", "2024-04-01"],
            ["2023-12-15", "2024-01-01", "2024-04-01"],
            ["2023-12-31", "2024-03-31", "2024-04-01"],
        ]

        for i, test_case in enumerate(test_cases):
            dates = pick_dates_from_range(test_case[0], test_case[1], test_case[2], test_case[3], test_case[4])
            self.assertEqual(dates, expected[i])

    def test_pick_dates_from_range_custom_frequency(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 15),
            datetime.date(2024, 3, 20),
            "C",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-15", "2024-03-20"])

        result = pick_dates_from_range(
            "2024-01-15",
            "2024-03-20",
            "C",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-15", "2024-03-20"])

        result = pick_dates_from_range(
            datetime.date(2024, 1, 15),
            "2024-03-20",
            "C",
            True,
            False,
        )
        self.assertEqual(result, ["2024-01-15", "2024-03-20"])

    def test_pick_dates_from_range_invalid_frequency(self):
        with self.assertRaises(ValueError) as context:
            pick_dates_from_range(
                datetime.date(2024, 1, 1),
                datetime.date(2024, 12, 31),
                "X",
                False,
                True,
            )
        self.assertIn("Invalid frequency", str(context.exception))

    def test_pick_dates_from_range_invalid_date_order(self):
        with self.assertRaises(ValueError) as context:
            pick_dates_from_range(
                datetime.date(2024, 12, 31),
                datetime.date(2024, 1, 1),
                "M",
                False,
                True,
            )
        self.assertIn("must be less than or equal to", str(context.exception))

    def test_pick_dates_from_range_same_date(self):
        result = pick_dates_from_range(
            datetime.date(2024, 6, 15),
            datetime.date(2024, 6, 15),
            "D",
            False,
            True,
        )
        self.assertEqual(result, ["2024-06-15"])

    def test_pick_dates_from_range_weekend_handling(self):
        result = pick_dates_from_range(
            datetime.date(2024, 9, 7),
            datetime.date(2024, 9, 8),
            "D",
            True,
            True,
        )
        self.assertEqual(result, [])

        result = pick_dates_from_range(
            datetime.date(2024, 9, 6),
            datetime.date(2024, 9, 9),
            "D",
            True,
            True,
        )
        self.assertEqual(result, ["2024-09-06", "2024-09-09"])

    def test_pick_dates_from_range_monthly_weekend_adjustment(self):
        result = pick_dates_from_range(
            datetime.date(2024, 6, 1),
            datetime.date(2024, 8, 31),
            "M",
            True,
            True,
        )
        self.assertIn("2024-06-03", result)

    def test_pick_dates_from_range_string_input(self):
        result = pick_dates_from_range(
            "2024-01-01",
            "2024-03-31",
            "M",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-01", "2024-02-01", "2024-03-01"])

    def test_pick_dates_from_range_empty_result(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 2),
            datetime.date(2024, 1, 3),
            "Y",
            False,
            False,
        )
        self.assertEqual(result, [])

    def test_pick_dates_from_range_no_duplicates(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "Q",
            False,
            True,
        )
        self.assertEqual(len(result), len(set(result)))

    def test_pick_dates_from_range_quarterly_business_days(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "Q",
            True,
            True,
        )
        for date_str in result:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            self.assertTrue(date_obj.weekday() < 5, f"{date_str} is not a business day")

    def test_pick_dates_from_range_half_yearly_start(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-01", "2024-07-01"])

        result = pick_dates_from_range(
            datetime.date(2023, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 3, 15),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-03-15", "2024-07-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 9, 15),
            datetime.date(2025, 6, 30),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-09-15", "2025-01-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 6, 30),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 7, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-07-01"])

    def test_pick_dates_from_range_half_yearly_end(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2024-06-30", "2024-12-31"])

        result = pick_dates_from_range(
            datetime.date(2023, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2023-06-30", "2023-12-31", "2024-06-30", "2024-12-31"])

        result = pick_dates_from_range(
            datetime.date(2024, 2, 15),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2024-06-30", "2024-12-31"])

        result = pick_dates_from_range(
            datetime.date(2024, 8, 15),
            datetime.date(2025, 3, 31),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2024-12-31", "2025-03-31"])

        result = pick_dates_from_range(
            datetime.date(2024, 5, 1),
            datetime.date(2024, 8, 31),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2024-06-30", "2024-08-31"])

    def test_pick_dates_from_range_half_yearly_with_business_days(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            True,
            True,
        )
        self.assertEqual(result, ["2024-01-01", "2024-07-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            True,
            False,
        )
        self.assertEqual(result, ["2024-06-28", "2024-12-31"])

        result = pick_dates_from_range(
            datetime.date(2024, 6, 1),
            datetime.date(2024, 12, 31),
            "HY",
            True,
            True,
        )
        self.assertIn("2024-06-03", result)
        self.assertIn("2024-07-01", result)

        result = pick_dates_from_range(
            datetime.date(2023, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            True,
            True,
        )
        self.assertIn("2023-01-02", result)
        self.assertIn("2023-07-03", result)
        self.assertIn("2024-01-01", result)
        self.assertIn("2024-07-01", result)

    def test_pick_dates_from_range_half_yearly_string_input(self):
        result = pick_dates_from_range(
            "2024-01-01",
            "2024-12-31",
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-01", "2024-07-01"])

        result = pick_dates_from_range(
            "2024-01-01",
            "2024-12-31",
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2024-06-30", "2024-12-31"])

    def test_pick_dates_from_range_half_yearly_leap_year(self):
        result = pick_dates_from_range(
            datetime.date(2024, 2, 29),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-02-29", "2024-07-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, ["2024-06-30", "2024-12-31"])

    def test_pick_dates_from_range_half_yearly_edge_cases(self):
        result = pick_dates_from_range(
            datetime.date(2024, 1, 1),
            datetime.date(2024, 6, 30),
            "HY",
            False,
            True,
        )
        self.assertEqual(result, ["2024-01-01"])

        result = pick_dates_from_range(
            datetime.date(2024, 2, 1),
            datetime.date(2024, 2, 28),
            "HY",
            False,
            False,
        )
        self.assertEqual(result, [])

        result = pick_dates_from_range(
            datetime.date(2022, 1, 1),
            datetime.date(2024, 12, 31),
            "HY",
            False,
            True,
        )
        self.assertEqual(
            result,
            [
                "2022-01-01",
                "2022-07-01",
                "2023-01-01",
                "2023-07-01",
                "2024-01-01",
                "2024-07-01",
            ],
        )
