import base64

from django.conf import settings
from django.core.exceptions import FieldError, ImproperlyConfigured
from django.db import models
from django.utils.encoding import force_bytes, force_str
from django.utils.functional import cached_property

from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

__all__ = [
    "EncryptedField",
    "EncryptedTextField",
    "EncryptedCharField",
    "EncryptedEmailField",
    "EncryptedIntegerField",
    "EncryptedDateField",
    "EncryptedDateTimeField",
]

backend = default_backend()
info = b"django-fernet-fields"
# We need reproducible key derivation, so we can't use a random salt
salt = b"django-fernet-fields-hkdf-salt"


class EncryptedField(models.Field):
    """A field that encrypts values using Fernet symmetric encryption."""

    _internal_type = "BinaryField"

    def __init__(self, *args, **kwargs):
        if kwargs.get("primary_key"):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} does not support primary_key=True."
            )
        if kwargs.get("unique"):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} does not support unique=True."
            )
        if kwargs.get("db_index"):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} does not support db_index=True."
            )
        super(EncryptedField, self).__init__(*args, **kwargs)

    @cached_property
    def keys(self):
        keys = getattr(settings, "FERNET_KEYS", None)
        if keys is None:
            keys = [settings.SECRET_KEY]
        return keys

    @cached_property
    def fernet_keys(self):
        if getattr(settings, "FERNET_USE_HKDF", True):
            return [derive_fernet_key(k) for k in self.keys]
        return self.keys

    @cached_property
    def fernet(self):
        if len(self.fernet_keys) == 1:
            return Fernet(self.fernet_keys[0])
        return MultiFernet([Fernet(k) for k in self.fernet_keys])

    def get_internal_type(self):
        return self._internal_type

    def get_db_prep_save(self, value, connection):
        value = super(EncryptedField, self).get_db_prep_save(value, connection)
        if value is not None:
            retval = self.fernet.encrypt(force_bytes(value))
            return connection.Database.Binary(retval)

    def from_db_value(self, value, expression, connection, *args):
        if value is not None:
            value = bytes(value)
            return self.to_python(force_str(self.fernet.decrypt(value)))

    @cached_property
    def validators(self):
        # Temporarily pretend to be whatever type of field we're masquerading
        # as, for purposes of constructing validators (needed for
        # IntegerField and subclasses).
        self.__dict__["_internal_type"] = super(
            EncryptedField, self
        ).get_internal_type()
        try:
            return super(EncryptedField, self).validators
        finally:
            del self.__dict__["_internal_type"]


def derive_fernet_key(input_key):
    """Derive a 32-bit b64-encoded Fernet key from arbitrary input key."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
        backend=backend,
    )
    return base64.urlsafe_b64encode(hkdf.derive(force_bytes(input_key)))


def get_prep_lookup(self):
    """Raise errors for unsupported lookups"""
    raise FieldError(
        f"{self.lhs.field.__class__.__name__} '{self.lookup_name}' "
        f"does not support lookups"
    )


# Register all field lookups (except 'isnull') to our handler
for name, lookup in models.Field.class_lookups.items():
    # Dynamically create classes that inherit from the right lookups
    if name != "isnull":
        lookup_class = type(
            f"EncryptedField{name}",
            (lookup,),
            {"get_prep_lookup": get_prep_lookup},
        )
        EncryptedField.register_lookup(lookup_class)


class EncryptedTextField(EncryptedField, models.TextField):
    pass


class EncryptedCharField(EncryptedField, models.CharField):
    pass


class EncryptedEmailField(EncryptedField, models.EmailField):
    pass


class EncryptedIntegerField(EncryptedField, models.IntegerField):
    pass


class EncryptedDateField(EncryptedField, models.DateField):
    pass


class EncryptedDateTimeField(EncryptedField, models.DateTimeField):
    pass
