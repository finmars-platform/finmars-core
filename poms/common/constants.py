from django.utils.translation import ugettext_lazy

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
    (NUMBER, ugettext_lazy('Number')),
    (STRING, ugettext_lazy('String')),
    (DATE, ugettext_lazy('Date')),
    (CLASSIFIER, ugettext_lazy('Classifier')),
    (BOOLEAN, ugettext_lazy('Boolean')),
    (SYSTEM_ATTRIBUTE, ugettext_lazy('System Attribute')),
    (USER_ATTRIBUTE, ugettext_lazy('User Attribute')),
    (RELATION, ugettext_lazy('Relation')),
    (SELECTOR, ugettext_lazy('Selector')),
    (BUTTON, ugettext_lazy('Button')),
    (DATETIME, ugettext_lazy('Datetime'))
)

class SystemValueType():
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