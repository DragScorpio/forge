from dedupe import dedupe


def test_preserves_first_seen_order():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_no_duplicates_unchanged():
    assert dedupe(["b", "a", "c"]) == ["b", "a", "c"]
