# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Buzzer component"""

from .atoms import CallbackComponent, PortIn


class Buzzer(CallbackComponent):
    """Buzzer component class"""

    TONE_TO_FREQUENCY = {
        "A": 880,
        "B": 987.77,
        "C": 1046.5,
        "D": 1174.66,
        "E": 1318.51,
        "F": 1396.91,
        "G": 1567.98,
    }

    def __init__(self, circuit, name=None, tone="A"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "I"))
        self.parameter_set("tone", tone)

    @property
    def active(self):
        return self.I.has_driver() and self.I.value == 1

    def tone_frequency(self):
        """Get frequency for tone"""
        return self.TONE_TO_FREQUENCY[self.parameter_get("tone")]

    @classmethod
    def get_parameters(cls):
        return {
            "tone": {
                "type": "list",
                "items": ["A", "B", "C", "D", "E", "F", "G"],
                "default": "A",
                "description": "Buzzer tone",
                "reconfigurable": True,
            },
        }
