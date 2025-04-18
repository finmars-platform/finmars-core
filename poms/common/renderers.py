from json.encoder import (
    INFINITY,
    _make_iterencode,
    encode_basestring,
    encode_basestring_ascii,
)

from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder


class CustomJSONEncoder(JSONEncoder):

    def iterencode(self, o, _one_shot=False):
        """
        Encode the given object and yield each string representation as available.
        For example::
            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)
        """
        # Hack to enforce
        c_make_encoder = None
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring

        def floatstr(o, allow_nan=self.allow_nan,
                     _repr=float.__repr__, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'null'
            elif o == _neginf:
                text = 'null'
            else:
                return _repr(o)

            # Somehow inf get passed and exception throwed
            # but we converted inf to null

            # if not allow_nan:
            #     raise ValueError(
            #         "Out of range float values are not JSON compliant: " +
            #         repr(o))

            return text

        if _one_shot and c_make_encoder is not None and self.indent is None:
            _iterencode = c_make_encoder(
                markers,
                self.default,
                _encoder,
                self.indent,
                self.key_separator,
                self.item_separator,
                self.sort_keys,
                self.skipkeys,
                self.allow_nan,
            )
        else:
            _iterencode = _make_iterencode(
                markers,
                self.default,
                _encoder,
                self.indent,
                floatstr,
                self.key_separator,
                self.item_separator,
                self.sort_keys,
                self.skipkeys,
                _one_shot,
            )
        return _iterencode(o, 0)


class FinmarsJSONRenderer(JSONRenderer):
    encoder_class = CustomJSONEncoder
