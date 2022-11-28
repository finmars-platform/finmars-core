# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function

from difflib import ndiff, SequenceMatcher

from diff_match_patch import diff_match_patch


def test1():
    obj1 = {
        'num': 1.2341,
        'list': [1, 2, 3],
    }
    obj2 = {
        'num': 1.23512,
        'list': [1, 3, 5],
    }
    print('obj1', obj1)
    print('obj2', obj2)
    a = str(obj1)
    b = str(obj2)

    print('-' * 79)
    for line in ndiff([a], [b]):
        print(line)

    print('-' * 79)
    m = SequenceMatcher(None, a, b)
    print(m.get_matching_blocks())
    for tag, i1, i2, j1, j2 in m.get_opcodes():
        print("%7s a[%d:%d] (%s) b[%d:%d] (%s)" % (tag, i1, i2, a[i1:i2], j1, j2, b[j1:j2]))

    print('-' * 79)
    m = diff_match_patch()
    print(m.diff_main(a, b))


def main():
    test1()


if __name__ == "__main__":
    main()
