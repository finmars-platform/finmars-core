import os
import warnings


def ENV_BOOL(env_name, default):
    val = os.environ.get(env_name, default)

    if val is None:
        return default

    if isinstance(val, bool):
        return val

    if val.lower() == "true":
        return True

    if val.lower() == "false":
        return False

    warnings.warn(f"Boolean var {env_name} has value {val}, return False")
    return False


def ENV_STR(env_name, default):
    val = os.environ.get(env_name, default)
    return val or default


def ENV_INT(env_name, default):
    val = os.environ.get(env_name, default)
    return int(val) if val else default
