import pytest

from calculator import divide


def test_divide_positive_numbers():
    assert divide(10, 2) == 5


def test_divide_different_numbers():
    assert divide(9, 3) == 3


def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)