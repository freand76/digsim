# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module with the functional (word-level) yosys cells, like $add, $mux and $dffe

A netlist synthesized with functional cells (see Synthesis) has far fewer cells than one
synthesized with gates, so it simulates faster. The cells are implemented from the
specification in https://github.com/YosysHQ/yosys/blob/main/techlibs/common/simlib.v

Each bit of a cell port is a port of its own, since the bits of a port can connect to
different nets. A value is kept as a number and a mask of the bits that are undefined
("X"), and an arithmetic result with an undefined input is undefined, as in Verilog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from digsim.utils import YosysCell
from digsim.utils._yosys_netlist import NET_TYPE

from .atoms import VALUE_TYPE, Component, Port, PortOutDelta, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


# A value of a port: the bits, and a mask of the bits that are undefined ("X")
Word = tuple[int, int]


def _mask(width: int) -> int:
    return (1 << width) - 1


def _signed(value: int, width: int) -> int:
    """A value of 'width' bits as a two's complement number"""
    if width > 0 and (value >> (width - 1)) & 1:
        return value - (1 << width)
    return value


def _extend(word: Word, width: int, signed: bool, new_width: int) -> Word:
    """A value extended (or cut) to new_width bits, with its sign bit if signed"""
    if new_width == width:
        return word
    value, undefined = word
    if new_width > width and signed and width > 0:
        fill = _mask(new_width) & ~_mask(width)
        if (undefined >> (width - 1)) & 1:
            undefined |= fill
        elif (value >> (width - 1)) & 1:
            value |= fill
    return value & _mask(new_width), undefined & _mask(new_width)


def _undefined(width: int) -> Word:
    return 0, _mask(width)


class _CellInput(PortWire):
    """
    One bit of an input of a functional cell. It keeps the cell's copy of the port value
    up to date, so that the cell doesn't read all the bits of a wide port for every bit
    that changes. A bit that doesn't change doesn't update the cell either.
    """

    def __init__(
        self, parent: Component, name: str, word: list[int], bit: int, update: bool
    ) -> None:
        self._word = word
        self._bit_mask = 1 << bit
        self._update = update
        super().__init__(parent, name)

    def set_value(self, value: VALUE_TYPE) -> None:
        if value == self._value:
            return
        if self._wired_ports:
            self.update_wires(value)
        else:
            self._value = value
        word = self._word
        mask = self._bit_mask
        if value == 1:
            word[0] |= mask
            word[1] &= ~mask
        elif value == 0:
            word[0] &= ~mask
            word[1] &= ~mask
        else:
            word[0] &= ~mask
            word[1] |= mask
        if self._update:
            self._parent.update()


class FunctionalCell(Component):
    """
    The base class of the functional cells. Inputs that change the output at once update
    the cell, data inputs of flip-flops are only read (at the clock edge). An output bit
    only gets an event when it changes, since every event updates the components it
    drives.
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name)
        self._cell = cell
        self._bits: dict[str, list[Port]] = {}
        # The value of each input port: [bits, undefined bits]
        self._inputs: dict[str, list[int]] = {}
        # The last value written to each output port, None before the first one
        self._outputs: dict[str, Word | None] = {}
        self._output_masks: dict[str, int] = {}
        self._params: dict[str, int] = {}

    def param(self, name: str, default: int = 0) -> int:
        """A parameter of the cell, as a number (read once, it is used in every update)"""
        if name not in self._params:
            self._params[name] = self._cell.parameter(name, default)
        return self._params[name]

    def width(self, name: str) -> int:
        """The width of a cell port"""
        return len(self._cell.connections.get(name, []))

    def add_input(self, name: str, update: bool = True) -> None:
        """Add an input port, its bits update the cell (or are only read, update=False)"""
        width = self.width(name)
        word = [0, _mask(width)]
        ports: list[Port] = [
            _CellInput(self, f"{name}[{bit}]", word, bit, update) for bit in range(width)
        ]
        for port in ports:
            self.add_port(port)
        self._bits[name] = ports
        self._inputs[name] = word

    def add_output(self, name: str) -> None:
        """Add an output port"""
        ports: list[Port] = [
            PortOutDelta(self, f"{name}[{bit}]") for bit in range(self.width(name))
        ]
        for port in ports:
            self.add_port(port)
        self._bits[name] = ports
        self._outputs[name] = None
        self._output_masks[name] = _mask(len(ports))

    def cell_port(self, name: str, bit: int) -> Port:
        """The port of one bit of a cell port"""
        return self._bits[name][bit]

    def init(self) -> None:
        super().init()
        # All ports are "X" after init, and the first value of each output bit gets an event
        for name, word in self._inputs.items():
            word[0] = 0
            word[1] = _mask(len(self._bits[name]))
        for name in self._outputs:
            self._outputs[name] = None

    def read(self, name: str) -> Word:
        """The value of an input port"""
        word = self._inputs[name]
        return word[0], word[1]

    def write(self, name: str, word: Word) -> None:
        """Set an output port, an event for each bit that changes"""
        ports = self._bits[name]
        mask = self._output_masks[name]
        undefined = word[1] & mask
        value = word[0] & ~undefined & mask
        last = self._outputs[name]
        if last is None:
            changed = mask
        else:
            changed = (value ^ last[0]) | (undefined ^ last[1])
            if not changed:
                return
        self._outputs[name] = (value, undefined)
        while changed:
            low = changed & -changed
            changed ^= low
            port = ports[low.bit_length() - 1]
            port.value = "X" if undefined & low else (1 if value & low else 0)


# --------------------------------------------------------------------------------------
# Combinational cells
# --------------------------------------------------------------------------------------


class UnaryCell(FunctionalCell):
    """A cell with the input A and the output Y"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_output("Y")
        self._a_width = self.width("A")
        self._a_signed = bool(self.param("A_SIGNED"))
        self._y_width = self.width("Y")

    def a_value(self) -> Word:
        """A, extended to the width of Y"""
        return _extend(self.read("A"), self._a_width, self._a_signed, self._y_width)

    def update(self) -> None:
        self.write("Y", self.compute())

    def compute(self) -> Word:
        """The value of Y"""
        raise NotImplementedError


class BinaryCell(FunctionalCell):
    """A cell with the inputs A and B, and the output Y"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_output("Y")
        self._a_width = self.width("A")
        self._b_width = self.width("B")
        self._y_width = self.width("Y")
        # Verilog: an operation is signed only if both operands are
        self._signed = bool(self.param("A_SIGNED")) and bool(self.param("B_SIGNED"))
        self._width = max(self._a_width, self._b_width, self._y_width)
        self._y_mask = _mask(self._y_width)

    def operands(self) -> tuple[int, int] | None:
        """A and B as numbers (signed if the operation is), or None if one is undefined"""
        a, a_undefined = self.read("A")
        b, b_undefined = self.read("B")
        if a_undefined or b_undefined:
            return None
        if self._signed:
            return _signed(a, self._a_width), _signed(b, self._b_width)
        return a, b

    def update(self) -> None:
        self.write("Y", self.compute())

    def compute(self) -> Word:
        """The value of Y"""
        raise NotImplementedError


class _Bitwise(BinaryCell):
    """A bitwise operation, on A and B extended to the width of Y"""

    def compute(self) -> Word:
        width = self._y_width
        a = _extend(self.read("A"), self._a_width, self._signed, width)
        b = _extend(self.read("B"), self._b_width, self._signed, width)
        return self.bitwise(a, b, self._y_mask)

    def bitwise(self, a: Word, b: Word, mask: int) -> Word:
        """The operation on two values with undefined bits"""
        raise NotImplementedError


def _known(word: Word, mask: int) -> tuple[int, int]:
    """The bits that are known to be 1, and the bits that are known to be 0"""
    value, undefined = word
    return value & ~undefined & mask, ~(value | undefined) & mask


class And(_Bitwise):
    """module \\$and (A, B, Y)"""

    def bitwise(self, a: Word, b: Word, mask: int) -> Word:
        a_ones, a_zeros = _known(a, mask)
        b_ones, b_zeros = _known(b, mask)
        ones = a_ones & b_ones
        return ones, mask & ~(ones | a_zeros | b_zeros)


class Or(_Bitwise):
    """module \\$or (A, B, Y)"""

    def bitwise(self, a: Word, b: Word, mask: int) -> Word:
        a_ones, a_zeros = _known(a, mask)
        b_ones, b_zeros = _known(b, mask)
        ones = a_ones | b_ones
        return ones, mask & ~(ones | (a_zeros & b_zeros))


class Xor(_Bitwise):
    """module \\$xor (A, B, Y)"""

    def bitwise(self, a: Word, b: Word, mask: int) -> Word:
        undefined = (a[1] | b[1]) & mask
        return (a[0] ^ b[0]) & ~undefined & mask, undefined


class Xnor(_Bitwise):
    """module \\$xnor (A, B, Y)"""

    def bitwise(self, a: Word, b: Word, mask: int) -> Word:
        undefined = (a[1] | b[1]) & mask
        return ~(a[0] ^ b[0]) & ~undefined & mask, undefined


class Not(UnaryCell):
    """module \\$not (A, Y)"""

    def compute(self) -> Word:
        value, undefined = self.a_value()
        return ~value & ~undefined & _mask(self._y_width), undefined


class Pos(UnaryCell):
    """module \\$pos (A, Y)"""

    def compute(self) -> Word:
        return self.a_value()


class Buf(Pos):
    """module \\$buf (A, Y)"""


class Neg(UnaryCell):
    """module \\$neg (A, Y)"""

    def compute(self) -> Word:
        value, undefined = self.a_value()
        if undefined:
            return _undefined(self._y_width)
        return -value & _mask(self._y_width), 0


class _Reduce(UnaryCell):
    """A reduction of A to one bit, zero-extended to the width of Y"""

    def compute(self) -> Word:
        value, undefined = self.read("A")
        result = self.reduce(value, undefined, _mask(self._a_width))
        if result is None:
            return 0, 1
        return result, 0

    def reduce(self, value: int, undefined: int, mask: int) -> int | None:
        """The bit, or None if it is undefined"""
        raise NotImplementedError


def _reduce_or(value: int, undefined: int) -> int | None:
    if value & ~undefined:
        return 1
    return None if undefined else 0


class ReduceAnd(_Reduce):
    """module \\$reduce_and (A, Y)"""

    def reduce(self, value: int, undefined: int, mask: int) -> int | None:
        if ~(value | undefined) & mask:
            return 0
        return None if undefined else 1


class ReduceOr(_Reduce):
    """module \\$reduce_or (A, Y)"""

    def reduce(self, value: int, undefined: int, mask: int) -> int | None:
        return _reduce_or(value, undefined)


class ReduceBool(ReduceOr):
    """module \\$reduce_bool (A, Y)"""


class ReduceXor(_Reduce):
    """module \\$reduce_xor (A, Y)"""

    def reduce(self, value: int, undefined: int, mask: int) -> int | None:
        return None if undefined else value.bit_count() & 1


class ReduceXnor(_Reduce):
    """module \\$reduce_xnor (A, Y)"""

    def reduce(self, value: int, undefined: int, mask: int) -> int | None:
        return None if undefined else 1 - (value.bit_count() & 1)


class LogicNot(_Reduce):
    """module \\$logic_not (A, Y)"""

    def reduce(self, value: int, undefined: int, mask: int) -> int | None:
        result = _reduce_or(value, undefined)
        return None if result is None else 1 - result


class _Logic(BinaryCell):
    """A logic operation on A and B as booleans, one bit zero-extended to Y"""

    def compute(self) -> Word:
        a = _reduce_or(*self.read("A"))
        b = _reduce_or(*self.read("B"))
        result = self.logic(a, b)
        return (0, 1) if result is None else (result, 0)

    def logic(self, a: int | None, b: int | None) -> int | None:
        """The result, None if it is undefined"""
        raise NotImplementedError


class LogicAnd(_Logic):
    """module \\$logic_and (A, B, Y)"""

    def logic(self, a: int | None, b: int | None) -> int | None:
        if a == 0 or b == 0:
            return 0
        return 1 if a == 1 and b == 1 else None


class LogicOr(_Logic):
    """module \\$logic_or (A, B, Y)"""

    def logic(self, a: int | None, b: int | None) -> int | None:
        if a == 1 or b == 1:
            return 1
        return 0 if a == 0 and b == 0 else None


class _Compare(BinaryCell):
    """A comparison of A and B, one bit zero-extended to Y"""

    def compute(self) -> Word:
        operands = self.operands()
        if operands is None:
            return 0, 1
        return int(self.compare(*operands)), 0

    def compare(self, a: int, b: int) -> bool:
        """The result of the comparison"""
        raise NotImplementedError


class Lt(_Compare):
    """module \\$lt (A, B, Y)"""

    def compare(self, a: int, b: int) -> bool:
        return a < b


class Le(_Compare):
    """module \\$le (A, B, Y)"""

    def compare(self, a: int, b: int) -> bool:
        return a <= b


class Gt(_Compare):
    """module \\$gt (A, B, Y)"""

    def compare(self, a: int, b: int) -> bool:
        return a > b


class Ge(_Compare):
    """module \\$ge (A, B, Y)"""

    def compare(self, a: int, b: int) -> bool:
        return a >= b


class Eq(BinaryCell):
    """module \\$eq (A, B, Y)"""

    _equal = 1

    def compute(self) -> Word:
        a_word = self._inputs["A"]
        b_word = self._inputs["B"]
        if not a_word[1] and not b_word[1] and self._a_width == self._b_width:
            # All bits defined, and nothing to extend
            return (self._equal if a_word[0] == b_word[0] else 1 - self._equal), 0
        a = _extend(self.read("A"), self._a_width, self._signed, self._width)
        b = _extend(self.read("B"), self._b_width, self._signed, self._width)
        mask = _mask(self._width)
        a_ones, a_zeros = _known(a, mask)
        b_ones, b_zeros = _known(b, mask)
        if (a_ones & b_zeros) | (a_zeros & b_ones):
            # A bit differs, whatever the undefined bits are
            return 1 - self._equal, 0
        if a[1] | b[1]:
            return 0, 1
        return self._equal, 0


class Ne(Eq):
    """module \\$ne (A, B, Y)"""

    _equal = 0


class Eqx(BinaryCell):
    """module \\$eqx (A, B, Y), "X" bits are compared as values"""

    _equal = 1

    def compute(self) -> Word:
        a = _extend(self.read("A"), self._a_width, self._signed, self._width)
        b = _extend(self.read("B"), self._b_width, self._signed, self._width)
        return (self._equal if a == b else 1 - self._equal), 0


class Nex(Eqx):
    """module \\$nex (A, B, Y)"""

    _equal = 0


class _Arithmetic(BinaryCell):
    """An arithmetic operation, its result cut to the width of Y"""

    def compute(self) -> Word:
        operands = self.operands()
        if operands is None:
            return _undefined(self._y_width)
        result = self.arithmetic(*operands)
        if result is None:
            return _undefined(self._y_width)
        return result & _mask(self._y_width), 0

    def arithmetic(self, a: int, b: int) -> int | None:
        """The result, None if it is undefined (like a division by zero)"""
        raise NotImplementedError


class Add(_Arithmetic):
    """module \\$add (A, B, Y)"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return a + b


class Sub(_Arithmetic):
    """module \\$sub (A, B, Y)"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return a - b


class Mul(_Arithmetic):
    """module \\$mul (A, B, Y)"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return a * b


def _truncated_div(a: int, b: int) -> int:
    """Division rounded towards zero, as in Verilog"""
    quotient = abs(a) // abs(b)
    return quotient if (a < 0) == (b < 0) else -quotient


class Div(_Arithmetic):
    """module \\$div (A, B, Y), rounded towards zero"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return None if b == 0 else _truncated_div(a, b)


class Mod(_Arithmetic):
    """module \\$mod (A, B, Y), with the sign of A"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return None if b == 0 else a - b * _truncated_div(a, b)


class DivFloor(_Arithmetic):
    """module \\$divfloor (A, B, Y), rounded down"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return None if b == 0 else a // b


class ModFloor(_Arithmetic):
    """module \\$modfloor (A, B, Y), with the sign of B"""

    def arithmetic(self, a: int, b: int) -> int | None:
        return None if b == 0 else a % b


class Pow(_Arithmetic):
    """module \\$pow (A, B, Y)"""

    def arithmetic(self, a: int, b: int) -> int | None:
        if b >= 0:
            # Only the bits of Y are kept
            return pow(a, b, 1 << self._y_width)
        if a == 1:
            return 1
        if a == -1:
            return 1 if b % 2 == 0 else -1
        return None if a == 0 else 0


class _Shift(BinaryCell):
    """A shift of A by B bits"""

    def compute(self) -> Word:
        b, b_undefined = self.read("B")
        if b_undefined:
            return _undefined(self._y_width)
        a_signed = bool(self.param("A_SIGNED"))
        width = max(self._a_width, self._y_width)
        a = _extend(self.read("A"), self._a_width, a_signed, width)
        return self.shift(a, b, width, a_signed)

    def shift(self, a: Word, b: int, width: int, a_signed: bool) -> Word:
        """The shifted value"""
        raise NotImplementedError

    def _result(self, word: Word) -> Word:
        mask = _mask(self._y_width)
        return word[0] & mask, word[1] & mask


def _shift_left(word: Word, amount: int, width: int) -> Word:
    if amount >= width:
        return 0, 0
    return word[0] << amount, word[1] << amount


def _shift_right(word: Word, amount: int, width: int, fill: Word = (0, 0)) -> Word:
    """Shift right, the top bits get the value of 'fill' (a sign bit)"""
    amount = min(amount, width)
    fill_mask = _mask(width) & ~_mask(width - amount)
    value = (word[0] >> amount) | (fill_mask if fill[0] else 0)
    undefined = (word[1] >> amount) | (fill_mask if fill[1] else 0)
    return value, undefined


class Shl(_Shift):
    """module \\$shl (A, B, Y)"""

    def shift(self, a: Word, b: int, width: int, a_signed: bool) -> Word:
        return self._result(_shift_left(a, b, width))


class Sshl(Shl):
    """module \\$sshl (A, B, Y)"""


class Shr(_Shift):
    """module \\$shr (A, B, Y), a logical shift"""

    def shift(self, a: Word, b: int, width: int, a_signed: bool) -> Word:
        return self._result(_shift_right(a, b, width))


class Sshr(_Shift):
    """module \\$sshr (A, B, Y), an arithmetic shift if A is signed"""

    def shift(self, a: Word, b: int, width: int, a_signed: bool) -> Word:
        sign = ((a[0] >> (width - 1)) & 1, (a[1] >> (width - 1)) & 1) if a_signed else (0, 0)
        return self._result(_shift_right(a, b, width, sign))


class Shift(_Shift):
    """module \\$shift (A, B, Y), to the right by B (to the left if B is negative)"""

    def compute(self) -> Word:
        b, b_undefined = self.read("B")
        if b_undefined:
            return _undefined(self._y_width)
        amount = _signed(b, self._b_width) if self.param("B_SIGNED") else b
        a_signed = bool(self.param("A_SIGNED"))
        width = max(self._a_width, self._y_width)
        a = _extend(self.read("A"), self._a_width, a_signed, width)
        if amount >= 0:
            return self._result(_shift_right(a, amount, width))
        return self._result(_shift_left(a, -amount, width))


class Shiftx(FunctionalCell):
    """module \\$shiftx (A, B, Y), bits from outside A are undefined"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_output("Y")
        self._a_width = self.width("A")
        self._b_width = self.width("B")
        self._y_width = self.width("Y")

    def update(self) -> None:
        b, b_undefined = self.read("B")
        if b_undefined:
            self.write("Y", _undefined(self._y_width))
            return
        amount = _signed(b, self._b_width) if self.param("B_SIGNED") else b
        a, a_undefined = self.read("A")
        value = 0
        undefined = 0
        for bit in range(self._y_width):
            source = bit + amount
            if 0 <= source < self._a_width:
                value |= ((a >> source) & 1) << bit
                undefined |= ((a_undefined >> source) & 1) << bit
            else:
                undefined |= 1 << bit
        self.write("Y", (value, undefined))


# --------------------------------------------------------------------------------------
# Multiplexers
# --------------------------------------------------------------------------------------


def _select(s: Word, a: Word, b: Word, mask: int) -> Word:
    """a if s is 0, b if s is 1, and with an undefined s the bits a and b agree on"""
    if not s[1]:
        return b if s[0] else a
    same = ~(a[0] ^ b[0]) & ~a[1] & ~b[1] & mask
    return a[0] & same, mask & ~same


class Mux(FunctionalCell):
    """module \\$mux (A, B, S, Y)"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_input("S")
        self.add_output("Y")
        self._mask = _mask(self.width("Y"))

    def update(self) -> None:
        self.write("Y", _select(self.read("S"), self.read("A"), self.read("B"), self._mask))


class Pmux(FunctionalCell):
    """
    module \\$pmux (A, B, S, Y): A if no bit of S is set, the part of B for the bit of S
    that is set, and undefined if more than one is
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_input("S")
        self.add_output("Y")
        self._y_width = self.width("Y")

    def update(self) -> None:
        s, s_undefined = self.read("S")
        if s_undefined or s & (s - 1):
            self.write("Y", _undefined(self._y_width))
        elif s == 0:
            self.write("Y", self.read("A"))
        else:
            b, b_undefined = self.read("B")
            shift = (s.bit_length() - 1) * self._y_width
            mask = _mask(self._y_width)
            self.write("Y", ((b >> shift) & mask, (b_undefined >> shift) & mask))


class Bmux(FunctionalCell):
    """module \\$bmux (A, S, Y): part S of A"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("S")
        self.add_output("Y")
        self._y_width = self.width("Y")

    def update(self) -> None:
        s, s_undefined = self.read("S")
        if s_undefined:
            self.write("Y", _undefined(self._y_width))
            return
        a, a_undefined = self.read("A")
        shift = s * self._y_width
        mask = _mask(self._y_width)
        self.write("Y", ((a >> shift) & mask, (a_undefined >> shift) & mask))


class Demux(FunctionalCell):
    """module \\$demux (A, S, Y): A in part S of Y, the other parts are 0"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("S")
        self.add_output("Y")
        self._a_width = self.width("A")

    def update(self) -> None:
        s, s_undefined = self.read("S")
        if s_undefined:
            self.write("Y", _undefined(self.width("Y")))
            return
        a, a_undefined = self.read("A")
        shift = s * self._a_width
        self.write("Y", (a << shift, a_undefined << shift))


class Bwmux(FunctionalCell):
    """module \\$bwmux (A, B, S, Y): each bit from B where S is set, from A where not"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_input("S")
        self.add_output("Y")
        self._mask = _mask(self.width("Y"))

    def update(self) -> None:
        a, a_undefined = self.read("A")
        b, b_undefined = self.read("B")
        s, s_undefined = self.read("S")
        mask = self._mask
        value = (a & ~s) | (b & s)
        undefined = (a_undefined & ~s) | (b_undefined & s)
        # An undefined select bit gives the value A and B agree on
        same = ~(a ^ b) & ~a_undefined & ~b_undefined
        undefined = (undefined & ~s_undefined) | (s_undefined & ~same)
        value &= ~undefined
        self.write("Y", (value & mask, undefined & mask))


# --------------------------------------------------------------------------------------
# Flip-flops and latches
# --------------------------------------------------------------------------------------


class _Register(FunctionalCell):
    """
    A flip-flop or latch, with the output Q. Like the gate flip-flops, it starts at 0. A
    control input is active at its polarity, and not active when it is undefined.
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self._width = self.param("WIDTH", self.width("Q"))
        self._mask = _mask(self._width)
        self._q: Word = (0, 0)
        self._old_clock: VALUE_TYPE = "X"

    def init(self) -> None:
        super().init()
        self._q = (0, 0)
        self._old_clock = "X"

    def default_state(self) -> None:
        self._q = (0, 0)
        self.write("Q", self._q)

    def control_active(self, port_name: str, polarity_name: str) -> bool:
        """Is a one-bit control input active"""
        return self._bits[port_name][0].value == self.param(polarity_name)

    def clock_edge(self) -> bool:
        """Did the clock change to its active level since the last update"""
        clock = self._bits["CLK"][0].value
        edge = clock != self._old_clock and clock == self.param("CLK_POLARITY")
        self._old_clock = clock
        return edge

    def set_q(self, word: Word) -> None:
        self._q = word
        self.write("Q", word)

    def update(self) -> None:
        raise NotImplementedError


class Dff(_Register):
    """module \\$dff (CLK, D, Q)"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("D", update=False)
        self.add_output("Q")

    def update(self) -> None:
        if self.clock_edge():
            self.set_q(self.read("D"))


class Dffe(_Register):
    """module \\$dffe (CLK, EN, D, Q)"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("EN", update=False)
        self.add_input("D", update=False)
        self.add_output("Q")

    def update(self) -> None:
        if self.clock_edge() and self.control_active("EN", "EN_POLARITY"):
            self.set_q(self.read("D"))


class Adff(_Register):
    """module \\$adff (CLK, ARST, D, Q), with an asynchronous reset"""

    _enable = False

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("ARST")
        if self._enable:
            self.add_input("EN", update=False)
        self.add_input("D", update=False)
        self.add_output("Q")
        self._reset_value = self.param("ARST_VALUE") & self._mask

    def update(self) -> None:
        edge = self.clock_edge()
        if self.control_active("ARST", "ARST_POLARITY"):
            self.set_q((self._reset_value, 0))
        elif edge and (not self._enable or self.control_active("EN", "EN_POLARITY")):
            self.set_q(self.read("D"))


class Adffe(Adff):
    """module \\$adffe (CLK, ARST, EN, D, Q)"""

    _enable = True


class Aldff(_Register):
    """module \\$aldff (CLK, ALOAD, AD, D, Q), with an asynchronous load of AD"""

    _enable = False

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("ALOAD")
        self.add_input("AD")
        if self._enable:
            self.add_input("EN", update=False)
        self.add_input("D", update=False)
        self.add_output("Q")

    def update(self) -> None:
        edge = self.clock_edge()
        if self.control_active("ALOAD", "ALOAD_POLARITY"):
            self.set_q(self.read("AD"))
        elif edge and (not self._enable or self.control_active("EN", "EN_POLARITY")):
            self.set_q(self.read("D"))


class Aldffe(Aldff):
    """module \\$aldffe (CLK, ALOAD, AD, EN, D, Q)"""

    _enable = True


class Sdff(_Register):
    """module \\$sdff (CLK, SRST, D, Q), with a synchronous reset"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("SRST", update=False)
        self.add_input("D", update=False)
        self.add_output("Q")
        self._reset_value = self.param("SRST_VALUE") & self._mask

    def update(self) -> None:
        if self.clock_edge():
            if self.control_active("SRST", "SRST_POLARITY"):
                self.set_q((self._reset_value, 0))
            else:
                self.set_q(self.read("D"))


class Sdffe(_Register):
    """module \\$sdffe (CLK, SRST, EN, D, Q), the reset also when not enabled"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("SRST", update=False)
        self.add_input("EN", update=False)
        self.add_input("D", update=False)
        self.add_output("Q")
        self._reset_value = self.param("SRST_VALUE") & self._mask

    def update(self) -> None:
        if not self.clock_edge():
            return
        if self.control_active("SRST", "SRST_POLARITY"):
            self.set_q((self._reset_value, 0))
        elif self.control_active("EN", "EN_POLARITY"):
            self.set_q(self.read("D"))


class Sdffce(Sdffe):
    """module \\$sdffce (CLK, SRST, EN, D, Q), the reset only when enabled"""

    def update(self) -> None:
        if not self.clock_edge() or not self.control_active("EN", "EN_POLARITY"):
            return
        if self.control_active("SRST", "SRST_POLARITY"):
            self.set_q((self._reset_value, 0))
        else:
            self.set_q(self.read("D"))


def _set_clear(
    q: Word, set_bits: Word, clear_bits: Word, set_on: int, clear_on: int, mask: int
) -> Word:
    """Q with the bits that are set or cleared (clear first), at their polarities"""
    set_active = (set_bits[0] if set_on else ~set_bits[0]) & ~set_bits[1] & mask
    clear_active = (clear_bits[0] if clear_on else ~clear_bits[0]) & ~clear_bits[1] & mask
    set_active &= ~clear_active
    value = (q[0] | set_active) & ~clear_active
    undefined = q[1] & ~(set_active | clear_active)
    return value, undefined


class Dffsr(_Register):
    """module \\$dffsr (CLK, SET, CLR, D, Q), with an asynchronous set and clear per bit"""

    _enable = False

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("CLK")
        self.add_input("SET")
        self.add_input("CLR")
        if self._enable:
            self.add_input("EN", update=False)
        self.add_input("D", update=False)
        self.add_output("Q")

    def update(self) -> None:
        q = self._q
        if self.clock_edge() and (not self._enable or self.control_active("EN", "EN_POLARITY")):
            q = self.read("D")
        q = _set_clear(
            q,
            self.read("SET"),
            self.read("CLR"),
            self.param("SET_POLARITY"),
            self.param("CLR_POLARITY"),
            self._mask,
        )
        self.set_q(q)


class Dffsre(Dffsr):
    """module \\$dffsre (CLK, SET, CLR, EN, D, Q)"""

    _enable = True


class Dlatch(_Register):
    """module \\$dlatch (EN, D, Q), transparent while enabled"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("EN")
        self.add_input("D")
        self.add_output("Q")

    def update(self) -> None:
        if self.control_active("EN", "EN_POLARITY"):
            self.set_q(self.read("D"))


class Adlatch(_Register):
    """module \\$adlatch (EN, ARST, D, Q)"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("EN")
        self.add_input("ARST")
        self.add_input("D")
        self.add_output("Q")
        self._reset_value = self.param("ARST_VALUE") & self._mask

    def update(self) -> None:
        if self.control_active("ARST", "ARST_POLARITY"):
            self.set_q((self._reset_value, 0))
        elif self.control_active("EN", "EN_POLARITY"):
            self.set_q(self.read("D"))


class Dlatchsr(_Register):
    """module \\$dlatchsr (EN, SET, CLR, D, Q)"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("EN")
        self.add_input("SET")
        self.add_input("CLR")
        self.add_input("D")
        self.add_output("Q")

    def update(self) -> None:
        q = self.read("D") if self.control_active("EN", "EN_POLARITY") else self._q
        q = _set_clear(
            q,
            self.read("SET"),
            self.read("CLR"),
            self.param("SET_POLARITY"),
            self.param("CLR_POLARITY"),
            self._mask,
        )
        self.set_q(q)


class Sr(_Register):
    """module \\$sr (SET, CLR, Q)"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("SET")
        self.add_input("CLR")
        self.add_output("Q")

    def update(self) -> None:
        q = _set_clear(
            self._q,
            self.read("SET"),
            self.read("CLR"),
            self.param("SET_POLARITY"),
            self.param("CLR_POLARITY"),
            self._mask,
        )
        self.set_q(q)


# --------------------------------------------------------------------------------------
# Cells of other synthesis flows: arithmetic building blocks, lookup tables and wiring.
# The functional synthesis of Synthesis doesn't make them, but other netlists can have
# them, for example with alumacc ($alu, $macc_v2) or LUT mapping ($lut).
# --------------------------------------------------------------------------------------


class Alu(FunctionalCell):
    """
    module \\$alu (A, B, CI, BI, X, Y, CO): Y = A + (B or ~B, if BI) + CI, with X the XOR
    of the operands and CO the carry out of each bit
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        for port in ("A", "B", "CI", "BI"):
            self.add_input(port)
        for port in ("X", "Y", "CO"):
            self.add_output(port)
        self._signed = bool(self.param("A_SIGNED")) and bool(self.param("B_SIGNED"))
        self._width = self.width("Y")
        self._mask = _mask(self._width)

    def update(self) -> None:
        width, mask = self._width, self._mask
        a = _extend(self.read("A"), self.width("A"), self._signed, width)
        b = _extend(self.read("B"), self.width("B"), self._signed, width)
        ci, ci_undefined = self.read("CI")
        bi, bi_undefined = self.read("BI")
        if bi_undefined:
            b = (0, mask)
        elif bi:
            b = (~b[0] & ~b[1] & mask, b[1])
        undefined = (a[1] | b[1]) & mask
        self.write("X", ((a[0] ^ b[0]) & ~undefined, undefined))
        if undefined or ci_undefined or bi_undefined:
            # As in Verilog, an undefined bit makes the sum and the carries undefined
            self.write("Y", _undefined(width))
            self.write("CO", _undefined(width))
            return
        total = a[0] + b[0] + ci
        self.write("Y", (total & mask, 0))
        # The carry into bit i+1 is the sum bit XOR the operand bits, for bit i+1
        self.write("CO", (((total ^ a[0] ^ b[0]) >> 1) & mask, 0))


class Lcu(FunctionalCell):
    """module \\$lcu (P, G, CI, CO): the carry out of each bit, from propagate and generate"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        for port in ("P", "G", "CI"):
            self.add_input(port)
        self.add_output("CO")
        self._width = self.width("CO")

    def update(self) -> None:
        p, p_undefined = self.read("P")
        g, g_undefined = self.read("G")
        carry, ci_undefined = self.read("CI")
        if p_undefined or g_undefined or ci_undefined:
            self.write("CO", _undefined(self._width))
            return
        co = 0
        for bit in range(self._width):
            carry = (g >> bit) & 1 | ((p >> bit) & 1 & carry)
            co |= carry << bit
        self.write("CO", (co, 0))


class Fa(FunctionalCell):
    """module \\$fa (A, B, C, X, Y): a full adder for each bit, Y the sum and X the carry"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        for port in ("A", "B", "C"):
            self.add_input(port)
        self.add_output("X")
        self.add_output("Y")
        self._mask = _mask(self.width("Y"))

    def update(self) -> None:
        a, a_undefined = self.read("A")
        b, b_undefined = self.read("B")
        c, c_undefined = self.read("C")
        undefined = (a_undefined | b_undefined | c_undefined) & self._mask
        self.write("Y", ((a ^ b ^ c) & ~undefined, undefined))
        self.write("X", (((a & b) | (c & (a ^ b))) & ~undefined, undefined))


class MaccV2(FunctionalCell):
    """
    module \\$macc_v2 (A, B, C, Y): Y is the sum of the products of the parts of A and B,
    and of the parts of C, each of them added or subtracted
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        for port in ("A", "B", "C"):
            self.add_input(port)
        self.add_output("Y")
        self._width = self.width("Y")

    def _parts(self, count: int, widths: int, signed: int) -> list[tuple[int, int, bool]]:
        """The (offset, width, signed) of each part of a port"""
        parts = []
        offset = 0
        for index in range(count):
            width = (widths >> (16 * index)) & 0xFFFF
            parts.append((offset, width, bool((signed >> index) & 1)))
            offset += width
        return parts

    def _operand(self, value: int, part: tuple[int, int, bool], signed: bool) -> int:
        offset, width, _ = part
        operand = (value >> offset) & _mask(width)
        return _signed(operand, width) if signed else operand

    def update(self) -> None:
        a, a_undefined = self.read("A")
        b, b_undefined = self.read("B")
        c, c_undefined = self.read("C")
        if a_undefined or b_undefined or c_undefined:
            self.write("Y", _undefined(self._width))
            return
        products = self.param("NPRODUCTS")
        addends = self.param("NADDENDS")
        a_parts = self._parts(products, self.param("A_WIDTHS"), self.param("A_SIGNED"))
        b_parts = self._parts(products, self.param("B_WIDTHS"), self.param("B_SIGNED"))
        c_parts = self._parts(addends, self.param("C_WIDTHS"), self.param("C_SIGNED"))
        total = 0
        for index in range(products):
            # Signed only if both factors are
            signed = a_parts[index][2] and b_parts[index][2]
            product = self._operand(a, a_parts[index], signed) * self._operand(
                b, b_parts[index], signed
            )
            total += -product if (self.param("PRODUCT_NEGATED") >> index) & 1 else product
        for index in range(addends):
            addend = self._operand(c, c_parts[index], c_parts[index][2])
            total += -addend if (self.param("ADDEND_NEGATED") >> index) & 1 else addend
        self.write("Y", (total & _mask(self._width), 0))


class Lut(FunctionalCell):
    """module \\$lut (A, Y): bit A of the table LUT"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_output("Y")

    def update(self) -> None:
        a, a_undefined = self.read("A")
        if a_undefined:
            self.write("Y", (0, 1))
        else:
            self.write("Y", ((self.param("LUT") >> a) & 1, 0))


class Sop(FunctionalCell):
    """
    module \\$sop (A, Y): a sum of products, Y is 1 if A matches one of the DEPTH terms
    in TABLE (two bits for each bit of A: 01 for a 0, 10 for a 1, 00 for either)
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_output("Y")
        width = self.width("A")
        table = self.param("TABLE")
        # For each term: the bits of A that must be 0, and the ones that must be 1
        self._terms = []
        for term in range(self.param("DEPTH")):
            zeros = ones = 0
            for bit in range(width):
                pair = (table >> (2 * width * term + 2 * bit)) & 3
                if pair & 1:
                    zeros |= 1 << bit
                if pair & 2:
                    ones |= 1 << bit
            self._terms.append((zeros, ones))

    def update(self) -> None:
        a, a_undefined = self.read("A")
        maybe = False
        for zeros, ones in self._terms:
            if (a & zeros & ~a_undefined) or (~a & ones & ~a_undefined):
                # A known bit doesn't match the term
                continue
            if not (a_undefined & (zeros | ones)):
                self.write("Y", (1, 0))
                return
            maybe = True
        self.write("Y", (0, 1) if maybe else (0, 0))


class Bweqx(FunctionalCell):
    """module \\$bweqx (A, B, Y): for each bit, 1 if the bits of A and B are the same, "X" too"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_output("Y")
        self._mask = _mask(self.width("Y"))

    def update(self) -> None:
        a, a_undefined = self.read("A")
        b, b_undefined = self.read("B")
        differ = (a ^ b) | (a_undefined ^ b_undefined)
        self.write("Y", (~differ & self._mask, 0))


class Concat(FunctionalCell):
    """module \\$concat (A, B, Y): Y = {B, A}"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("B")
        self.add_output("Y")
        self._a_width = self.width("A")

    def update(self) -> None:
        a, a_undefined = self.read("A")
        b, b_undefined = self.read("B")
        shift = self._a_width
        self.write("Y", (a | (b << shift), a_undefined | (b_undefined << shift)))


class Slice(FunctionalCell):
    """module \\$slice (A, Y): Y = A >> OFFSET"""

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_output("Y")
        self._offset = self.param("OFFSET")

    def update(self) -> None:
        a, a_undefined = self.read("A")
        self.write("Y", (a >> self._offset, a_undefined >> self._offset))


class Tribuf(FunctionalCell):
    """
    module \\$tribuf (A, EN, Y): A when enabled, otherwise high impedance, which is "X"
    in DigSim (it has no high impedance value)
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_input("EN")
        self.add_output("Y")
        self._width = self.width("Y")

    def update(self) -> None:
        enable = self._bits["EN"][0].value
        self.write("Y", self.read("A") if enable == 1 else _undefined(self._width))


# The functional cells by their Yosys cell type
FUNCTIONAL_CELLS: dict[str, type[FunctionalCell]] = {
    "$not": Not,
    "$pos": Pos,
    "$buf": Buf,
    "$neg": Neg,
    "$and": And,
    "$or": Or,
    "$xor": Xor,
    "$xnor": Xnor,
    "$reduce_and": ReduceAnd,
    "$reduce_or": ReduceOr,
    "$reduce_xor": ReduceXor,
    "$reduce_xnor": ReduceXnor,
    "$reduce_bool": ReduceBool,
    "$logic_not": LogicNot,
    "$logic_and": LogicAnd,
    "$logic_or": LogicOr,
    "$shl": Shl,
    "$shr": Shr,
    "$sshl": Sshl,
    "$sshr": Sshr,
    "$shift": Shift,
    "$shiftx": Shiftx,
    "$lt": Lt,
    "$le": Le,
    "$eq": Eq,
    "$ne": Ne,
    "$eqx": Eqx,
    "$nex": Nex,
    "$ge": Ge,
    "$gt": Gt,
    "$add": Add,
    "$sub": Sub,
    "$mul": Mul,
    "$div": Div,
    "$mod": Mod,
    "$divfloor": DivFloor,
    "$modfloor": ModFloor,
    "$pow": Pow,
    "$mux": Mux,
    "$pmux": Pmux,
    "$bmux": Bmux,
    "$demux": Demux,
    "$bwmux": Bwmux,
    "$dff": Dff,
    "$dffe": Dffe,
    "$adff": Adff,
    "$adffe": Adffe,
    "$aldff": Aldff,
    "$aldffe": Aldffe,
    "$sdff": Sdff,
    "$sdffe": Sdffe,
    "$sdffce": Sdffce,
    "$dffsr": Dffsr,
    "$dffsre": Dffsre,
    "$dlatch": Dlatch,
    "$adlatch": Adlatch,
    "$dlatchsr": Dlatchsr,
    "$sr": Sr,
    "$alu": Alu,
    "$lcu": Lcu,
    "$fa": Fa,
    "$macc_v2": MaccV2,
    "$lut": Lut,
    "$sop": Sop,
    "$bweqx": Bweqx,
    "$concat": Concat,
    "$slice": Slice,
    "$tribuf": Tribuf,
}

# Cells without outputs, for formal verification and simulation messages
IGNORED_CELLS = {
    "$scopeinfo",
    "$print",
    "$check",
    "$assert",
    "$assume",
    "$cover",
    "$live",
    "$fair",
    "$specify2",
    "$specify3",
    "$specrule",
}


# --------------------------------------------------------------------------------------
# Decoders: comparisons of the same input with constants
# --------------------------------------------------------------------------------------

DECODER_TYPE = "$digsim_decoder"


class Decoder(FunctionalCell):
    """
    The $eq and $ne cells that compare the same input A with different constants, as one
    cell (made by group_comparisons()): output bit i is 1 if A is VALUE<i> (or if it is
    not, for a $ne cell, EQUAL<i> = 0). An instruction decoder or a state machine has many
    of them, and a change of A updates them all. As one cell, a change of A is one lookup.
    """

    def __init__(self, circuit: Circuit, name: str, cell: YosysCell) -> None:
        super().__init__(circuit, name, cell)
        self.add_input("A")
        self.add_output("Y")
        outputs = self.width("Y")
        self._values = [self.param(f"VALUE{index}") for index in range(outputs)]
        # The outputs when A matches none of the values: 1 for the $ne cells
        self._none = sum(
            1 << index for index in range(outputs) if not self.param(f"EQUAL{index}", 1)
        )
        # The outputs that change for each value of A
        self._flips: dict[int, int] = {}
        for index, value in enumerate(self._values):
            self._flips[value] = self._flips.get(value, 0) | (1 << index)

    def update(self) -> None:
        a, a_undefined = self.read("A")
        if not a_undefined:
            self.write("Y", (self._none ^ self._flips.get(a, 0), 0))
            return
        # Undefined bits: equal is undefined, unless a known bit differs
        value = self._none
        undefined = 0
        for index, constant in enumerate(self._values):
            if (a ^ constant) & ~a_undefined:
                continue
            undefined |= 1 << index
        self.write("Y", (value & ~undefined, undefined))


FUNCTIONAL_CELLS[DECODER_TYPE] = Decoder


def _constant(bits: list[NET_TYPE]) -> int | None:
    """The value of constant bits ("0" and "1", the first bit is the lowest), or None"""
    value = 0
    for index, bit in enumerate(bits):
        if bit == "1":
            value |= 1 << index
        elif bit != "0":
            return None
    return value


def group_comparisons(cells: dict[str, YosysCell]) -> dict[str, YosysCell]:
    """
    The cells, with the unsigned $eq and $ne cells that compare the same nets with
    constants replaced by one Decoder cell for each set of nets
    """
    groups: dict[tuple[NET_TYPE, ...], list[tuple[str, int, int]]] = {}
    for name, cell in cells.items():
        if cell.type not in ("$eq", "$ne") or len(cell.connections.get("Y", [])) != 1:
            continue
        if cell.parameter("A_SIGNED") and cell.parameter("B_SIGNED"):
            # A signed comparison extends the sign bits, only unsigned ones are grouped
            continue
        a, b = cell.connections["A"], cell.connections["B"]
        # The narrower one is extended with zeros, the constant can be any width
        constant = _constant(b)
        compared = a
        if constant is None:
            constant, compared = _constant(a), b
        if constant is None or _constant(compared) is not None:
            continue
        groups.setdefault(tuple(compared), []).append((name, constant, int(cell.type == "$eq")))

    grouped = {name for members in groups.values() if len(members) > 1 for name, _, _ in members}
    result = {name: cell for name, cell in cells.items() if name not in grouped}
    for number, (nets, members) in enumerate(groups.items()):
        if len(members) < 2:
            continue
        parameters: dict[str, str | int] = {}
        outputs: list[NET_TYPE] = []
        for index, (name, constant, equal) in enumerate(members):
            parameters[f"VALUE{index}"] = constant
            parameters[f"EQUAL{index}"] = equal
            outputs += cells[name].connections["Y"]
        result[f"$decoder${number}"] = YosysCell(
            type=DECODER_TYPE,
            port_directions={"A": "input", "Y": "output"},
            connections={"A": list(nets), "Y": outputs},
            parameters=parameters,
        )
    return result
