# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function

import random
import timeit
from collections import OrderedDict

import simpleeval

results = OrderedDict()


def test1(count, show=False):
    v = 0.
    for i in range(0, count):
        v += 100 * random.random() + i
    if show:
        print('v', v)
    results['test1'] = v


def test2(count, show=False):
    v = 0.
    for i in range(0, count):
        v += simpleeval.simple_eval('100 * rnd + i', names={'rnd': random.random(), 'i': i, })
    if show:
        print('v', v)
    results['test2'] = v


def test3(count, show=False):
    v = 0.
    s = simpleeval.SimpleEval()
    parsed = simpleeval.ast.parse('100 * rnd + i').body[0].value
    for i in range(0, count):
        s.names = {'rnd': random.random(), 'i': i, }
        v += s._eval(parsed)
    if show:
        print('v', v)
    results['test3'] = v


def main():
    count = 10000
    number = 1
    precision = 3

    test1(count, True)
    test2(count, True)
    test3(count, True)

    # return

    def test(prefix, func):
        times = timeit.repeat(func, number=number)
        print('%s: loops=%s, best=%.*g, times=%s' % (
            prefix, number, precision, min(times), ['%.*g' % (precision, t,) for t in times]))
        # if min(times) > 0.002:
        #     print(data)

    print('loops=%s, count=%s' % (number, count))
    test('              raw', lambda: test1(count))
    test('       simpleeval', lambda: test2(count))
    test('simpleeval_cached', lambda: test3(count))
    print(results)


if __name__ == "__main__":
    main()
