import json
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User

from poms.common.common_base_test import BaseTestCase
from poms.common.renderers import _DATE_FORMAT, _TIME_FORMAT, ExtendedJSONEncoder


class TestExtendedJSONEncoder(BaseTestCase):
    def setUp(self):
        self.encoder = ExtendedJSONEncoder()

    @BaseTestCase.cases(
        ("1", 3.14, "3.14"),
        ("2", -2.5, "-2.5"),
    )
    def test_good_floats(self, value, expected):
        self.assertEqual(self.encoder.encode(value), expected)

    @BaseTestCase.cases(
        ("nan", float("nan")),
        ("inf", float("inf")),
        ("ninf", float("-inf")),
    )
    def test_bad_floats(self, value):
        with self.assertRaises(ValueError) as e:
            self.encoder.encode(value)
            self.assertIn("float values are not JSON compliant", str(e))

    def test_datetime_serialization(self):
        dt = datetime(2025, 4, 7, 12, 30, 45)
        expected = f'"{dt.strftime(_TIME_FORMAT)}"'
        self.assertEqual(self.encoder.encode(dt), expected)

    def test_date_serialization(self):
        d = date(2025, 4, 7)
        expected = f'"{d.strftime(_DATE_FORMAT)}"'
        self.assertEqual(self.encoder.encode(d), expected)

    def test_queryset_object_serialization(self):
        User.objects.create(username="test1", email="test1@example.com")
        User.objects.create(username="test2", email="test2@example.com")

        queryset = User.objects.all()
        serialized = json.loads(self.encoder.encode(queryset))

        self.assertEqual(len(serialized), 2)
        self.assertEqual(serialized[0]["username"], "test1")
        self.assertEqual(serialized[1]["username"], "test2")

    def test_queryset_values_serialization(self):
        User.objects.create(username="test1", email="test1@example.com")
        User.objects.create(username="test2", email="test2@example.com")

        queryset = User.objects.values("username")
        serialized = json.loads(self.encoder.encode(queryset))

        self.assertEqual(len(serialized), 2)
        self.assertEqual(serialized[0]["username"], "test1")
        self.assertEqual(serialized[1]["username"], "test2")

    @BaseTestCase.cases(
        ("list", [1, 2, 3], "[1, 2, 3]"),
        ("dict", {"a": 1}, '{"a": 1}'),
        ("str", "string", '"string"'),
        ("true", True, "true"),
        ("false", False, "false"),
    )
    def test_non_handled_types(self, value, expected):
        """Test types that should fall back to default JSONEncoder."""
        self.assertEqual(self.encoder.encode(value), expected)

    @BaseTestCase.cases(
        ("1", "3.12345", "3.12345"),
        ("2", "-2.5", "-2.5"),
    )
    def test_decimals(self, value, expected):
        self.assertEqual(self.encoder.encode(Decimal(value)), expected)

    def test_nested_structures_with_floats(self):
        """Test complex nested structures with mixed types."""
        data = {
            "date": date(2023, 1, 1),
            "datetime": datetime(2023, 1, 1, 12, 1, 1),
            "float": 3.14,
            "decimal": Decimal("7.62"),
            "users": User.objects.all(),
            "nested": {"number": 1234, "list": [date(2023, 1, 2), Decimal(17.6789)]},
        }

        # Create test users
        User.objects.create(username="nested1")
        User.objects.create(username="nested2")

        result = json.loads(self.encoder.encode(data))

        self.assertEqual(result["date"], "2023-01-01")
        self.assertEqual(result["datetime"], "2023-01-01T12:01:01.000000Z")
        self.assertEqual(result["float"], 3.14)
        self.assertEqual(len(result["users"]), 2)
        self.assertEqual(result["nested"]["list"][0], "2023-01-02")

        self.assertEqual(result["nested"]["number"], 1234)
        self.assertEqual(result["decimal"], 7.62)
        self.assertEqual(result["nested"]["list"][1], 17.6789)

    def test_nested_structures_with_nan(self):
        data = {
            "nested": {"number": float("nan"), "list": [date(2023, 1, 2), 314]},
        }
        with self.assertRaises(ValueError) as e:
            _ = json.loads(self.encoder.encode(data))
            self.assertIn("float values are not JSON compliant", str(e))

    def test_nested_structures_with_inf(self):
        data = {
            "nested": {"number": float("inf"), "list": [date(2023, 1, 2), 2735.87]},
        }
        with self.assertRaises(ValueError) as e:
            _ = json.loads(self.encoder.encode(data))
            self.assertIn("float values are not JSON compliant", str(e))

    def test_nested_structures_with_minus_inf(self):
        data = {
            "nested": {"number": float("-inf"), "list": [date(2023, 1, 2), 172365]},
        }

        with self.assertRaises(ValueError) as e:
            _ = json.loads(self.encoder.encode(data))
            self.assertIn("float values are not JSON compliant", str(e))

    def test_empty_queryset(self):
        """Test serialization of empty QuerySet."""
        queryset = User.objects.none()
        serialized = json.loads(self.encoder.encode(queryset))
        self.assertEqual(serialized, [])
