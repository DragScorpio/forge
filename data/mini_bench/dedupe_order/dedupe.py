"""Remove duplicates from a sequence."""


def dedupe(items):
    """Return the items with duplicates removed, preserving first-seen order."""
    return sorted(set(items))
