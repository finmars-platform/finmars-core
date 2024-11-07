from poms.common.common_base_test import BaseTestCase

class TestExpressions(BaseTestCase):
    databases = "__all__"

    calc_period_date_formula_data = {
        "names1": {},
        "is_eval": True
    }

    calc_period_date_expected = {
        "names1": {},
        "names": {},
        "is_eval": True,
        "log": ""
    }

    def setUp(self):
        super().setUp()
        self.init_test_case()
        self.url = (
            f"/{self.realm_code}/{self.space_code}/api/v1/utils/expression/"
        )

    @BaseTestCase.cases(
        (
            "monthly",
            {
                **calc_period_date_formula_data,
                "expression": "calculate_period_date(\"2024-12-01\", \"M\", -3, False, False)"
            },
            {
                **calc_period_date_expected,
                "expression": "calculate_period_date(\"2024-12-01\", \"M\", -3, False, False)",
                "result": "2024-09-30"
            }
        ),
        (
            "monthly_business_days_start",
            {
                **calc_period_date_formula_data,
                "expression": "calculate_period_date(\"2024-12-01\", \"M\", 3, True, True)"
            },
            {
                **calc_period_date_expected,
                "expression": "calculate_period_date(\"2024-12-01\", \"M\", 3, True, True)",
                "result": "2025-03-03"
            }
        ),
        (
                "weekly_start",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date(\"2024-09-01\", \"W\", 2, False, True)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date(\"2024-09-01\", \"W\", 2, False, True)",
                    "result": "2024-09-09"
                }
        ),
        (
                "weekly_business_days",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date(\"2024-09-01\", \"W\", 2, True, False)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date(\"2024-09-01\", \"W\", 2, True, False)",
                    "result": "2024-09-13"
                }
        ),
        (
                "annually",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date('2024-12-01', 'Y', -1, False, False)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date('2024-12-01', 'Y', -1, False, False)",
                    "result": "2023-12-31"
                }
        ),
        (
                "daily",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date(\"2024-09-04\", \"D\", 3, True, True)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date(\"2024-09-04\", \"D\", 3, True, True)",
                    "result": "2024-09-09"
                }
        ),
        (
                "quarterly_start",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date(\"2024-01-01\", \"Q\", 1, False, True)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date(\"2024-01-01\", \"Q\", 1, False, True)",
                    "result": "2024-04-01"
                }
        ),
        (
                "quarterly",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date(\"2024-01-01\", \"Q\", 2, False, False)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date(\"2024-01-01\", \"Q\", 2, False, False)",
                    "result": "2024-06-30"
                }
        ),
        (
                "with_parse_date",
                {
                    **calc_period_date_formula_data,
                    "expression": "calculate_period_date(parse_date(\"2024-01-01\"), \"D\", 1, False, False)"
                },
                {
                    **calc_period_date_expected,
                    "expression": "calculate_period_date(parse_date(\"2024-01-01\"), \"D\", 1, False, False)",
                    "result": "2024-01-02"
                }
        )
    )
    def test__calculate_period_date(self, formula_data, expected_result):

        response = self.client.post(path=self.url, format="json", data=formula_data)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), expected_result)
