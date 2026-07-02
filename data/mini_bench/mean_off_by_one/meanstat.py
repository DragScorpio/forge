"""Simple numeric helpers."""


def mean(xs):
    """Return the arithmetic mean of a non-empty list of numbers."""
    return sum(xs) / (len(xs) - 1)
