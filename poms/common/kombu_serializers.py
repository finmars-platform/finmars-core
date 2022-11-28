import base64
import io
import pickle
import zlib

from django.core.signing import TimestampSigner
from kombu.serialization import register
from kombu.utils.encoding import bytes_to_str

__author__ = 'ailyukhin'


def register_pickle_signed(key=None, salt=None, compress=True):
    def signer():
        return TimestampSigner(key=key, salt=salt)

    def encoder(obj):
        d = pickle.dumps(obj)
        if compress:
            d = zlib.compress(d)
        d = base64.b64encode(d)
        # d = base64.encodebytes(d)
        d = signer().sign(d)
        # d = str_to_bytes(d)
        return d

    def decoder(s):
        d = bytes_to_str(s)
        d = signer().unsign(d)
        d = base64.b64decode(d)
        # d = d.encode()
        # d = base64.decodebytes(d)
        if compress:
            d = zlib.decompress(d)
        d = io.BytesIO(d)
        return pickle.load(d)

    register('pickle-signed', encoder, decoder,
             content_type='application/x-python-serialize-signed',
             content_encoding='utf-8')
