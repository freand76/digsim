# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with Logic Analyzer component"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from .atoms import CallbackComponent, Parameter, PortOutDelta, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class LogicAnalyzer(CallbackComponent):
    """
    A logic analyzer, keeps the last 100 samples of each input to show them in the GUI.

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
        for portname in self.PORTLIST:
            self.add_port(PortWire(self, portname))
            self.data_dict[portname] = [0] * 100
        self._feedback = PortOutDelta(self, "feedback")
        self._feedback.update_parent(True)
        self.parameter_set("sample_rate", sample_rate)
        self.reconfigure()

    def default_state(self) -> None:
        self._feedback.value = 1

    def update(self) -> None:
        if self._feedback.value == 1:
            self._feedback.value = 0
        else:
            self._feedback.value = 1

        # Replace the lists instead of changing them, the GUI thread reads them while painting
        for portname in self.PORTLIST:
            value = 1 if self.port(portname).value == 1 else 0
            self.data_dict[portname] = [*self.data_dict[portname][1:], value]
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
