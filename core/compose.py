# Composition helpers for Lab 7.
# compose and pipe both chain small functions into one bigger function,
# they just read in opposite order.

from functools import reduce


def compose(*funcs):
    # compose(f, g, h)(x) == f(g(h(x))) - right to left, like in math.
    def composed(x):
        return reduce(lambda value, f: f(value), reversed(funcs), x)

    return composed


def pipe(x, *funcs):
    # pipe(x, f, g, h) == h(g(f(x))) - left to right, like a pipeline.
    return reduce(lambda value, f: f(value), funcs, x)
