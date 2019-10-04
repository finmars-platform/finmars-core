from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_text

from poms.common.fields import SlugRelatedFilteredField, PrimaryKeyRelatedFilteredField
from poms.users.filters import OwnerByMasterUserFilter

