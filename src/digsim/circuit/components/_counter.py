# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Counter component module"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import (
    VALUE_TYPE,
    Component,
    ComponentException,
    Parameter,
    PortIn,
    PortOutDelta,
    PortWire,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit

MAX_WIDTH = 32


class Counter(Component):
    """
    A binary counter: Q counts up (or down) by one on each rising edge of clk, and wraps
    around. It starts at 0.

    Ports:
        clk: Clock input.
        R: Reset input, 1 sets Q to 0 at once.
        EN: Clock enable input, the clock edge is ignored while it is 0 (only with
            `enable`).
        UP: Direction input, 1 counts up and 0 down (only with `up_down`).
        LD: Load input, 1 loads D on the clock edge instead of counting (only with `load`).
        D: Data input to load, `width` bits (only with `load`).
        Q: Output, `width` bits.
        CO: Carry output, 1 at the last count before Q wraps around: the highest value
            counting up, 0 counting down.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 32.
        enable: Add the clock enable input EN.
        up_down: Add the direction input UP, otherwise it counts up.
        load: Add the load inputs LD and D.
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        width: int = 4,
        enable: bool = False,
        up_down: bool = False,
        load: bool = False,
    ) -> None:
        super().__init__(circuit, name)
        if not 1 <= width <= MAX_WIDTH:
            raise ComponentException(f"The width must be 1 to {MAX_WIDTH}")
        self._enable = enable
        self._up_down = up_down
        self._load = load
        self._mask = (1 << width) - 1
        self._count: VALUE_TYPE = 0
        self.add_port(PortIn(self, "clk"))
        self.add_port(PortIn(self, "R"))
        if enable:
            self.add_port(PortWire(self, "EN"))
        if up_down:
            self.add_port(PortIn(self, "UP"))
        if load:
            self.add_port(PortWire(self, "LD"))
            self.add_port(PortWire(self, "D", width=width))
        self.add_port(PortOutDelta(self, "Q", width=width))
        self.add_port(PortOutDelta(self, "CO"))
        self.parameter_set("width", width)
        self.parameter_set("enable", enable)
        self.parameter_set("up_down", up_down)
        self.parameter_set("load", load)

    def default_state(self) -> None:
        self._set_count(0)

    def _counts_up(self) -> VALUE_TYPE:
        return self.UP.value if self._up_down else 1

    def _set_count(self, count: VALUE_TYPE) -> None:
        self._count = count
        self.Q.value = count
        self._carry_out()

    def _carry_out(self) -> None:
        up = self._counts_up()
        if not isinstance(self._count, int) or not isinstance(up, int):
            self.CO.value = "X"
        else:
            self.CO.value = int(self._count == (self._mask if up else 0))

    def update(self) -> None:
        rising_edge = self.clk.is_rising_edge()
        if self.R.value == 1:
            if self._count != 0:
                self._set_count(0)
            return
        if not rising_edge:
            # The direction changed: the carry output follows it
            self._carry_out()
            return
        if self._enable and self.EN.value == 0:
            return
        if self._load and self.LD.value == 1:
            data = self.D.value
            self._set_count(data if isinstance(data, int) else "X")
            return
        up = self._counts_up()
        if not isinstance(self._count, int) or not isinstance(up, int):
            self._set_count("X")
            return
        self._set_count((self._count + (1 if up else -1)) & self._mask)

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": {
                "type": "int",
                "min": 1,
                "max": MAX_WIDTH,
                "default": 4,
                "description": "Bitwidth of the counter",
            },
            "enable": {"type": "bool", "default": False, "description": "Clock enable input EN"},
            "up_down": {
                "type": "bool",
                "default": False,
                "description": "Count up or down, direction input UP",
            },
            "load": {
                "type": "bool",
                "default": False,
                "description": "Load inputs LD and D",
            },
        }
