# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Values typed in the GUI, like the value of a circuit input (kept free from Qt imports so
that it can be tested without a display)
"""

from __future__ import annotations

from digsim.circuit.components.atoms import VALUE_TYPE


def parse_value(text: str, width: int, allow_z: bool = False) -> int | str:
    """
    A value typed as hexadecimal (0x2A), binary (0b101) or decimal (42), or "Z" (not
    driven) with allow_z.

    Raises:
        ValueError: If it isn't a number, or doesn't fit in 'width' bits.
    """
    text = text.strip().replace("_", "")
    if allow_z and text.upper() == "Z":
        return "Z"
    try:
        value = int(text, 0)
    except ValueError:
        raise ValueError(f"'{text}' is not a number") from None
    if not 0 <= value < 1 << width:
        raise ValueError(f"{value} does not fit in {width} bits")
    return value


def value_text(value: VALUE_TYPE, width: int) -> str:
    """A value as the GUI shows it: hexadecimal with all digits, a bit as 0 or 1"""
    if not isinstance(value, int):
        return str(value)
    if width == 1:
        return str(value)
    return f"{value:0{(width + 3) // 4}X}"
