# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Module with Logic Analyzer component"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from .atoms import VALUE_TYPE, CallbackComponent, Parameter, PortIn, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class LogicAnalyzer(CallbackComponent):
    """
    A logic analyzer, keeps the last 100 samples of each input to show them in the GUI.
    The samples are cleared when the circuit is initialized (a reset in the GUI).
    A sample is the value an input had just before the time of the sample: an input that
    changes at the same time, like on the edge of a clock, is sampled before the change,
    whatever the order of the events at that time.

    Ports:
        A, B, ..., H: Inputs.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        sample_rate: The samples per second.
    """

    PORTLIST: typing.ClassVar = ["A", "B", "C", "D", "E", "F", "G", "H"]

    def __init__(self, circuit: Circuit, name: str | None = None, sample_rate: int = 100) -> None:
        super().__init__(circuit, name)
        self.data_dict: dict[str, list[int]] = {}
        # The value of each input, the time it last changed, and its value before that
        self._values: dict[str, VALUE_TYPE] = {}
        self._changed_ns: dict[str, int] = {}
        self._before: dict[str, VALUE_TYPE] = {}
        for portname in self.PORTLIST:
            self.add_port(PortIn(self, portname))
            self.data_dict[portname] = [0] * 100
        self._feedback = PortOutDelta(self, "feedback")
        self._feedback.update_parent(True)
        # The level of the feedback, it toggles at each sample
        self._sample_level: VALUE_TYPE = "X"
        self.parameter_set("sample_rate", sample_rate)
        self.reconfigure()

    def default_state(self) -> None:
        # A new run from time 0, like the VCD file: the samples of the last one are gone
        self.data_dict = {portname: [0] * 100 for portname in self.PORTLIST}
        for portname in self.PORTLIST:
            self._values[portname] = self.port(portname).value
            self._changed_ns[portname] = -1
            self._before[portname] = self._values[portname]
        self._sample_level = "X"
        self._feedback.value = 1

    def update(self) -> None:
        now = self.circuit.time_ns
        level = self._feedback.value
        if level == self._sample_level:
            # An input changed
            for portname in self.PORTLIST:
                value = self.port(portname).value
                old = self._values.get(portname, "X")
                if value != old:
                    if self._changed_ns.get(portname) != now:
                        self._before[portname] = old
                        self._changed_ns[portname] = now
                    self._values[portname] = value
            return
        self._sample_level = level
        self._feedback.value = 0 if level == 1 else 1

        # Replace the lists instead of changing them, the GUI thread reads them while painting
        for portname in self.PORTLIST:
            value = (
                self._before[portname]
                if self._changed_ns.get(portname) == now
                else self.port(portname).value
            )
            self.data_dict[portname] = [*self.data_dict[portname][1:], 1 if value == 1 else 0]
        super().update()

    def reconfigure(self) -> None:
        sample_rate = self.parameter_get("sample_rate")
        period_ns = int(1000000000 / sample_rate)
        self._feedback.set_delay_ns(period_ns)

    def signal_data(self) -> dict[str, list[int]]:
        """Get the logic analyzer signal data"""
        return self.data_dict

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "sample_rate": {
                "type": "int",
                "min": 10,
                "max": 100,
                "default": 100,
                "description": "Sample rate in Hz",
                "reconfigurable": True,
            },
        }
