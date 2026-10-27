# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Arithmetic components: adder, subtractor, multiplier, comparator and negator"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import VALUE_TYPE, Component, ComponentException, Parameter, PortIn, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit

MAX_WIDTH = 32
# The product of a multiplier is twice as wide as its inputs
MAX_MULTIPLIER_WIDTH = 16


def _numbers(*values: VALUE_TYPE) -> list[int] | None:
    """The values as numbers, None if one of them is "X" or "Z" """
    numbers = [value for value in values if isinstance(value, int)]
    return numbers if len(numbers) == len(values) else None


def _width_parameter(maximum: int = MAX_WIDTH) -> Parameter:
    return {
        "type": "int",
        "min": 1,
        "max": maximum,
        "default": 8,
        "description": "Bitwidth of the inputs",
    }


class _Arithmetic(Component):
    """The base class of the arithmetic components, with inputs of 'width' bits"""

    MAX_WIDTH = MAX_WIDTH

    def __init__(self, circuit: Circuit, name: str | None, width: int) -> None:
        super().__init__(circuit, name)
        if not 1 <= width <= self.MAX_WIDTH:
            raise ComponentException(f"The width must be 1 to {self.MAX_WIDTH}")
        self._width = width
        self._mask = (1 << width) - 1
        self.parameter_set("width", width)


class Adder(_Arithmetic):
    """
    Adds two numbers: S is A + B (+ Cin), and Cout is the carry out.

    Ports:
        A: Input, `width` bits.
        B: Input, `width` bits.
        Cin: Carry input (only with `carry_in`).
        S: Sum output, `width` bits.
        Cout: Carry output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 32.
        carry_in: Add the carry input Cin, to chain adders.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, width: int = 8, carry_in: bool = False
    ) -> None:
        super().__init__(circuit, name, width)
        self._carry_in = carry_in
        self.add_port(PortIn(self, "A", width=width))
        self.add_port(PortIn(self, "B", width=width))
        if carry_in:
            self.add_port(PortIn(self, "Cin"))
        self.add_port(PortOutDelta(self, "S", width=width))
        self.add_port(PortOutDelta(self, "Cout"))
        self.parameter_set("carry_in", carry_in)

    def update(self) -> None:
        numbers = _numbers(self.A.value, self.B.value, self.Cin.value if self._carry_in else 0)
        if numbers is None:
            self.S.value = "X"
            self.Cout.value = "X"
            return
        total = sum(numbers)
        self.S.value = total & self._mask
        self.Cout.value = total >> self._width

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": _width_parameter(),
            "carry_in": {"type": "bool", "default": False, "description": "Carry input Cin"},
        }


class Subtractor(_Arithmetic):
    """
    Subtracts two numbers: D is A - B (- Bin), and Bout is 1 when it borrows (A is
    smaller).

    Ports:
        A: Input, `width` bits.
        B: Input, `width` bits.
        Bin: Borrow input (only with `borrow_in`).
        D: Difference output, `width` bits.
        Bout: Borrow output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 32.
        borrow_in: Add the borrow input Bin, to chain subtractors.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, width: int = 8, borrow_in: bool = False
    ) -> None:
        super().__init__(circuit, name, width)
        self._borrow_in = borrow_in
        self.add_port(PortIn(self, "A", width=width))
        self.add_port(PortIn(self, "B", width=width))
        if borrow_in:
            self.add_port(PortIn(self, "Bin"))
        self.add_port(PortOutDelta(self, "D", width=width))
        self.add_port(PortOutDelta(self, "Bout"))
        self.parameter_set("borrow_in", borrow_in)

    def update(self) -> None:
        numbers = _numbers(self.A.value, self.B.value, self.Bin.value if self._borrow_in else 0)
        if numbers is None:
            self.D.value = "X"
            self.Bout.value = "X"
            return
        a, b, borrow = numbers
        difference = a - b - borrow
        self.D.value = difference & self._mask
        self.Bout.value = 1 if difference < 0 else 0

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": _width_parameter(),
            "borrow_in": {"type": "bool", "default": False, "description": "Borrow input Bin"},
        }


class Multiplier(_Arithmetic):
    """
    Multiplies two numbers: P is A * B, twice as wide as them.

    Ports:
        A: Input, `width` bits.
        B: Input, `width` bits.
        P: Product output, 2 * `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits of A and B, 1 to 16.
    """

    MAX_WIDTH = MAX_MULTIPLIER_WIDTH

    def __init__(self, circuit: Circuit, name: str | None = None, width: int = 8) -> None:
        super().__init__(circuit, name, width)
        self.add_port(PortIn(self, "A", width=width))
        self.add_port(PortIn(self, "B", width=width))
        self.add_port(PortOutDelta(self, "P", width=2 * width))

    def update(self) -> None:
        numbers = _numbers(self.A.value, self.B.value)
        self.P.value = "X" if numbers is None else numbers[0] * numbers[1]

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {"width": _width_parameter(MAX_MULTIPLIER_WIDTH)}


class Comparator(_Arithmetic):
    """
    Compares two numbers: LT is 1 when A < B, EQ when A = B and GT when A > B.

    Ports:
        A: Input, `width` bits.
        B: Input, `width` bits.
        LT: Output, A is less than B.
        EQ: Output, A equals B.
        GT: Output, A is greater than B.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 32.
        signed: Compare A and B as two's complement numbers.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, width: int = 8, signed: bool = False
    ) -> None:
        super().__init__(circuit, name, width)
        self._signed = signed
        self.add_port(PortIn(self, "A", width=width))
        self.add_port(PortIn(self, "B", width=width))
        self.add_port(PortOutDelta(self, "LT"))
        self.add_port(PortOutDelta(self, "EQ"))
        self.add_port(PortOutDelta(self, "GT"))
        self.parameter_set("signed", signed)

    def _number(self, value: int) -> int:
        if self._signed and value >> (self._width - 1):
            return value - (1 << self._width)
        return value

    def update(self) -> None:
        numbers = _numbers(self.A.value, self.B.value)
        if numbers is None:
            for port in (self.LT, self.EQ, self.GT):
                port.value = "X"
            return
        a, b = (self._number(number) for number in numbers)
        self.LT.value = int(a < b)
        self.EQ.value = int(a == b)
        self.GT.value = int(a > b)

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": _width_parameter(),
            "signed": {
                "type": "bool",
                "default": False,
                "description": "Signed numbers (two's complement)",
            },
        }


class Negator(_Arithmetic):
    """
    Negates a number: Y is -A, in two's complement.

    Ports:
        A: Input, `width` bits.
        Y: Output, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 32.
    """

    def __init__(self, circuit: Circuit, name: str | None = None, width: int = 8) -> None:
        super().__init__(circuit, name, width)
        self.add_port(PortIn(self, "A", width=width))
        self.add_port(PortOutDelta(self, "Y", width=width))

    def update(self) -> None:
        numbers = _numbers(self.A.value)
        self.Y.value = "X" if numbers is None else -numbers[0] & self._mask

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {"width": _width_parameter()}
