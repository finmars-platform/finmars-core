from poms.common.common_base_test import BaseTestCase

from django.core.validators import ValidationError
from poms.common.fields import name_validator


class TestNameValidator(BaseTestCase):

    @BaseTestCase.cases(
        ("1", "validString"),
        ("2", "A1_b2_C3d_ewrt"),
        ("3", "x_y_z"),
        ("4", "abc"),
        ("5", "abc123de"),
    )
    def test_valid_strings(self, string):
        try:
            name_validator(string)
        except ValidationError:
            self.fail(f"raised ValidationError string: {string}")

    @BaseTestCase.cases(
        # ("1", "1invalid"),
        # ("2", "_invalid"),
        ("1", " invalid"),
        ("2", "invalid!"),
        ("3", "invalid-string"),
        ("4", ""),
        ("5", "invalid string"),
        ("6", "invalid@string"),
    )
    def test_invalid_strings(self, string):
        with self.assertRaises(ValidationError):
            name_validator(string)
