from jose import jwt

from poms_app import settings


def encode_with_jwt(payload):
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

    return encoded_jwt


def decoded_with_jwt(encoded_jwt):
    decoded_jwt = jwt.decode(encoded_jwt, settings.JWT_SECRET_KEY, algorithms=['HS256'])

    return decoded_jwt
