import copy
import logging

_l = logging.getLogger('poms.layout_recovery')


def recursive_fix(source, target):

    for key, value in source.items():

        if isinstance(source[key], dict):

            if key not in target:
                target[key] = {}

            recursive_fix(source[key], target[key])
        else:

            if not key in target:
                target[key] = source[key]

            else:
                if not target[key]:
                    target[key] = source[key]


def recursive_dict_fix(source, target):

    result = copy.deepcopy(target)

    recursive_fix(source, result)

    return result
