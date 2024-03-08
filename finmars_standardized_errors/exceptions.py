from rest_framework import exceptions
from django.utils.encoding import force_str
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

class FinmarsBaseException(Exception):
    def __init__(self, error_key: str, message: str = ""):
        """
        A custom exception for Finmars with an obligatory error_key property.

        :param error_key: A unique string key identifying the error.
        :param args: Additional arguments passed to the base Exception class.
        """
        super().__init__(message)
        self.error_key = error_key

    def __str__(self):
        """
        Returns a string representation of the exception, including the error key.
        """
        return super().__str__()
        # return f"{self.__class__.__name__}(error_key={self.error_key}, message={super().__str__()})"

    def __repr__(self):
        return super().__str__()


class ErrorDetail(str):
    """
    A string-like object that can additionally have a code.
    """
    code = None
    error_key = None

    def __new__(cls, string, code=None, error_key=None):
        self = super().__new__(cls, string)
        self.code = code
        self.error_key = error_key
        return self

    def __eq__(self, other):
        result = super().__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        try:
            return result and self.code == other.code
        except AttributeError:
            return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    def __repr__(self):
        return 'ErrorDetail(string=%r, code=%r, error_key=%r)' % (
            str(self),
            self.code,
            self.error_key
        )

    def __hash__(self):
        return hash(str(self))

def _get_error_details(data, default_code=None, error_key=None):
    """
    Descend into a nested data structure, forcing any
    lazy translation strings or strings into `ErrorDetail`.
    """
    if isinstance(data, (list, tuple)):
        ret = [
            _get_error_details(item, default_code) for item in data
        ]
        if isinstance(data, ReturnList):
            return ReturnList(ret, serializer=data.serializer)
        return ret
    elif isinstance(data, dict):
        ret = {
            key: _get_error_details(value, default_code)
            for key, value in data.items()
        }
        if isinstance(data, ReturnDict):
            return ReturnDict(ret, serializer=data.serializer)
        return ret

    text = force_str(data)
    code = getattr(data, 'code', default_code)
    return ErrorDetail(text, code, error_key)



class FinmarsApiException(exceptions.APIException):

    def __init__(self, detail=None, code=None, error_key=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        self.error_key = error_key

        print('FinmarsApiException %s' % self.error_key)

        self.detail = _get_error_details(detail, code, error_key)
