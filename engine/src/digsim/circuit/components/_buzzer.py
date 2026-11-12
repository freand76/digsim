# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Buzzer component"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from .atoms import CallbackComponent, Parameter, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class Buzzer(CallbackComponent):
    """
    A buzzer, plays a tone in the GUI while its input is 1.

    Ports:
        I: Input.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        tone: The note, "A" to "G".
    """

    TONE_TO_FREQUENCY: typing.ClassVar = {
        "A": 880,
        "B": 987.77,
        "C": 1046.5,
        "D": 1174.66,
        "E": 1318.51,
        "F": 1396.91,
        "G": 1567.98,
    }

    def __init__(self, circuit: Circuit, name: str | None = None, tone: str = "A") -> None:
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "I"))
        self.parameter_set("tone", tone)

    @property
    def active(self) -> bool:
        return self.I.has_driver() and self.I.value == 1

    def tone_frequency(self) -> float:
        """Get frequency for tone"""
        return self.TONE_TO_FREQUENCY[self.parameter_get("tone")]

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "tone": {
                "type": "list",
                "items": ["A", "B", "C", "D", "E", "F", "G"],
                "default": "A",
                "description": "Buzzer tone",
                "reconfigurable": True,
            },
        }
