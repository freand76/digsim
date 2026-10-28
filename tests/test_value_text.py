# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the values typed and shown in the GUI"""

import pytest

from digsim.app._value_text import parse_value, value_text


@pytest.mark.parametrize(
    ("text", "value"), [("42", 42), ("0x2A", 42), ("0b101", 5), (" 0xff ", 255), ("1_0", 10)]
)
def test_parse_value(text, value):
    assert parse_value(text, 8) == value


def test_parse_value_errors():
    with pytest.raises(ValueError, match="not a number"):
        parse_value("abc", 8)
    with pytest.raises(ValueError, match="does not fit"):
        parse_value("256", 8)
    with pytest.raises(ValueError, match="not a number"):
        parse_value("Z", 8)
    assert parse_value("z", 8, allow_z=True) == "Z"


def test_value_text():
    assert value_text(42, 8) == "2A"
    assert value_text(5, 12) == "005"
    assert value_text(1, 1) == "1"
    assert value_text("X", 4) == "X"
