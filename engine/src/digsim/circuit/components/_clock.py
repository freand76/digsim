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


# The highest frequency in the GUI, a half period of 5 ns
MAX_FREQUENCY = 100_000_000


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
        self._half_period_ns = 1
        self.parameter_set("frequency", frequency)
        self.reconfigure()

    def default_state(self) -> None:
        self.O.value = 0
        self._feedback.value = 1

    def update(self) -> None:
        if self._feedback.value == 1:
            self.O.value = 1
            self._feedback.value = 0
        else:
            self.O.value = 0
            self._feedback.value = 1
        super().update()

    def next_edge_ns(self, rising: bool = True) -> int:
        """
        The time of the next rising (or falling) edge of the output, in nanoseconds.

        Raises:
            DigsimException: If the circuit isn't initialized (the clock doesn't run).
        """
        # The output changes at the next event of the feedback
        edge = self.circuit.next_event_ns(self._feedback)
        if edge is None:
            raise DigsimException("The clock runs from Circuit.init()")
        if (self.O.value == 1) == rising:
            # The next change is the other edge
            edge += self._half_period_ns
        return edge

    @property
    def half_period_ns(self) -> int:
        """The time between two edges of the output, in nanoseconds"""
        return self._half_period_ns

    def reconfigure(self) -> None:
        self._half_period_ns = int(1000000000 / (self.parameter_get("frequency") * 2))
        self._feedback.set_delay_ns(self._half_period_ns)
        self.circuit.delay_changed(self._feedback)

    @property
    def active(self) -> bool:
        return self.O.value == 1

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "frequency": {
                "type": "frequency",
                "min": 1,
                "max": MAX_FREQUENCY,
                "default": 1,
                "description": "Clock frequency",
                "reconfigurable": True,
            },
        }
