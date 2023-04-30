import os
import warnings

def ENV_BOOL(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    if val == 'True' or val == True:
        return True

    if val == 'False' or val == False:
        return False

    warnings.warn('Variable %s is not boolean. It is %s' % (env_name, val))

def ENV_STR(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    return val

def ENV_INT(env_name, default):

    val = os.environ.get(env_name, default)

    if not val:
        return default

    return int(val)

