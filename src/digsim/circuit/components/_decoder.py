# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Decoder and demultiplexer components"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, ComponentException, Parameter, PortIn, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit

# The most select bits, for 16 outputs
MAX_SELECT = 4


def _select_parameter(default: int) -> Parameter:
    return {
        "type": "int",
        "min": 1,
        "max": MAX_SELECT,
        "default": default,
        "description": "Select bits (2^bits outputs)",
    }


class _Selector(Component):
    """The base class of the decoder and the demultiplexer: outputs Y0, Y1, ... by S"""

    def __init__(self, circuit: Circuit, name: str | None, select: int) -> None:
        super().__init__(circuit, name)
        if not 1 <= select <= MAX_SELECT:
            raise ComponentException(f"The select bits must be 1 to {MAX_SELECT}")
        self.parameter_set("select", select)

    def _add_outputs(self, select: int, width: int) -> None:
        self._outputs = [
            PortOutDelta(self, f"Y{index}", width=width) for index in range(1 << select)
        ]
        for port in self._outputs:
            self.add_port(port)


class Decoder(_Selector):
    """
    A decoder: the output that S selects is 1, the others are 0.

    Ports:
        S: Select input, `select` bits.
        EN: Enable input, all outputs are 0 while it is 0 (only with `enable`).
        Y0, Y1, ...: Outputs, one for each value of S.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        select: The number of select bits, 1 to 4 (2 to 16 outputs).
        enable: Add the enable input EN.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, select: int = 2, enable: bool = False
    ) -> None:
        super().__init__(circuit, name, select)
        self._enable = enable
        self.add_port(PortIn(self, "S", width=select))
        if enable:
            self.add_port(PortIn(self, "EN"))
        self._add_outputs(select, 1)
        self.parameter_set("enable", enable)

    def update(self) -> None:
        select = self.S.value
        enable = self.EN.value if self._enable else 1
        if enable == 0:
            for port in self._outputs:
                port.value = 0
        elif not isinstance(select, int) or enable != 1:
            for port in self._outputs:
                port.value = "X"
        else:
            for index, port in enumerate(self._outputs):
                port.value = int(index == select)

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "select": _select_parameter(2),
            "enable": {"type": "bool", "default": False, "description": "Enable input EN"},
        }


class Demultiplexer(_Selector):
    """
    A demultiplexer: the output that S selects is I, the others are 0.

    Ports:
        I: Input, `width` bits.
        S: Select input, `select` bits.
        Y0, Y1, ...: Outputs, `width` bits, one for each value of S.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        select: The number of select bits, 1 to 4 (2 to 16 outputs).
        width: The number of bits of I and the outputs, 1 to 32.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, select: int = 1, width: int = 1
    ) -> None:
        super().__init__(circuit, name, select)
        self.add_port(PortIn(self, "I", width=width))
        self.add_port(PortIn(self, "S", width=select))
        self._add_outputs(select, width)
        self.parameter_set("width", width)

    def update(self) -> None:
        select = self.S.value
        if not isinstance(select, int):
            for port in self._outputs:
                port.value = "X"
            return
        for index, port in enumerate(self._outputs):
            port.value = self.I.value if index == select else 0

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "select": _select_parameter(1),
            "width": {
                "type": "int",
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bitwidth of the input and the outputs",
            },
        }
