from django.utils.translation import gettext_lazy

STRING = 10
NUMBER = 20
CLASSIFIER = 30
DATE = 40
BOOLEAN = 50
SYSTEM_ATTRIBUTE = 60
USER_ATTRIBUTE = 70
DATETIME = 80

RELATION = 100
SELECTOR = 110
BUTTON = 120

SYSTEM_VALUE_TYPES = (
    (NUMBER, gettext_lazy("Number")),
    (STRING, gettext_lazy("String")),
    (DATE, gettext_lazy("Date")),
    (CLASSIFIER, gettext_lazy("Classifier")),
    (BOOLEAN, gettext_lazy("Boolean")),
    (SYSTEM_ATTRIBUTE, gettext_lazy("System Attribute")),
    (USER_ATTRIBUTE, gettext_lazy("User Attribute")),
    (RELATION, gettext_lazy("Relation")),
    (SELECTOR, gettext_lazy("Selector")),
    (BUTTON, gettext_lazy("Button")),
    (DATETIME, gettext_lazy("Datetime")),
)


class SystemValueType:
    STRING = 10
    NUMBER = 20
    CLASSIFIER = 30
    DATE = 40
    BOOLEAN = 50
    SYSTEM_ATTRIBUTE = 60
    USER_ATTRIBUTE = 70
    DATETIME = 80

    RELATION = 100
    SELECTOR = 110
    BUTTON = 120
