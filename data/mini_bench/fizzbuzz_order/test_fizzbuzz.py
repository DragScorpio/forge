from fizzbuzz import fizzbuzz


def test_fizzbuzz_15():
    assert fizzbuzz(15) == "FizzBuzz"


def test_fizzbuzz_basics():
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(7) == "7"
