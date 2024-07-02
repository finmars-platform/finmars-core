import random
import string
import datetime
import jwt

from poms_app import settings
from .models import FinmarsRefreshToken


def generate_random_string(N):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(N))


def get_refresh_token(bot, platform, ttl_minutes=60 * 8, *args, **kwargs):
    # Define the expiration time +1 hour from now
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=ttl_minutes)

    # Define the payload with the expiration time and username
    payload = {
        'username': bot.username,
        'realm_code': platform.realm_code,
        'space_code': platform.realm_code,
        'exp': expiration_time,
        'iat': datetime.datetime.utcnow()  # Issued at time
    }

    # Encode the JWT token
    jwt_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    token = FinmarsRefreshToken(jwt_token)

    return token
