from meanstat import mean


def test_mean_of_three():
    assert mean([2, 4, 6]) == 4.0


def test_mean_single_value():
    assert mean([7]) == 7.0
