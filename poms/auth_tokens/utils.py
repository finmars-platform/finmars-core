import string
import random


def generate_random_string(N):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(N))
