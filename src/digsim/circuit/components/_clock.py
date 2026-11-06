# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Clock component module"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import (
    CallbackComponent,
    DigsimException,
    Parameter,
    PortOutDelta,
    PortOutImmediate,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class Clock(CallbackComponent):
    """
    A clock, its output is a square wave. It starts low at init(), and rises half a period
    later. A test bench can drive a circuit by its edges, see Circuit.run_until_edge().

    Ports:
        O: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        frequency: The frequency in Hz.
    """

    def __init__(self, circuit: Circuit, name: str | None = None, frequency: int = 1) -> None:
        super().__init__(circuit, name)
        self._feedback = PortOutDelta(self, "feedback")
        portout = PortOutImmediate(self, "O")
        self.add_port(portout)
        self._feedback.update_parent(True)
        # When the output changes next (None before init())
        self._next_toggle_ns: int | None = None
        self.parameter_set("frequency", frequency)
        self.reconfigure()

    def default_state(self) -> None:
        self.O.value = 0
        self._feedback.value = 1
        self._next_toggle_ns = self.circuit.time_ns + self.half_period_ns

    def update(self) -> None:
        if self._feedback.value == 1:
            self.O.value = 1
            self._feedback.value = 0
        else:
            self.O.value = 0
            self._feedback.value = 1
        self._next_toggle_ns = self.circuit.time_ns + self.half_period_ns
        super().update()

    def next_edge_ns(self, rising: bool = True) -> int:
        """
        The time of the next rising (or falling) edge of the output, in nanoseconds.

        Raises:
            DigsimException: If the circuit isn't initialized (the clock doesn't run).
        """
        if self._next_toggle_ns is None:
            raise DigsimException("The clock runs from Circuit.init()")
        edge = self._next_toggle_ns
        if (self.O.value == 1) == rising:
            # The next change is the other edge
            edge += self.half_period_ns
        return edge

    @property
    def half_period_ns(self) -> int:
        """The time between two edges of the output, in nanoseconds"""
        return int(1000000000 / (self.parameter_get("frequency") * 2))

    def reconfigure(self) -> None:
        self._feedback.set_delay_ns(self.half_period_ns)

    @property
    def active(self) -> bool:
        return self.O.value == 1

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "frequency": {
                "type": "int",
                "min": 1,
                "max": 100,
                "default": 1,
                "description": "Clock frequency in Hz",
                "reconfigurable": True,
            },
        }
