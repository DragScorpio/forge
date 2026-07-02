"""Parse a single 'key=value' configuration line."""


def parse_kv(line):
    """Split 'key=value' into a (key, value) tuple."""
    key, value = line.split("=")
    return key, value
