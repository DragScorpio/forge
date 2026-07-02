from kvparse import parse_kv


def test_value_with_equals():
    assert parse_kv("url=http://host/path?a=1&b=2") == ("url", "http://host/path?a=1&b=2")


def test_simple_pair():
    assert parse_kv("name=forge") == ("name", "forge")
