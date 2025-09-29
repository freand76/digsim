# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Clock component module"""

from .atoms import CallbackComponent, PortOutDelta, PortOutImmediate


class Clock(CallbackComponent):
    """Clock component class"""

    def __init__(self, circuit, name=None, frequency=1):
        super().__init__(circuit, name)
        self._feedback = PortOutDelta(self, "feedback")
        portout = PortOutImmediate(self, "O")
        self.add_port(portout)
        self._feedback.update_parent(True)
        self.parameter_set("frequency", frequency)
        self.reconfigure()

    def default_state(self):
        self.O.value = 0
        self._feedback.value = 1

    def update(self):
        if self._feedback.value == 1:
            self.O.value = 1
            self._feedback.value = 0
        else:
            self.O.value = 0
            self._feedback.value = 1
        super().update()

    def reconfigure(self):
        frequency = self.parameter_get("frequency")
        half_period_ns = int(1000000000 / (frequency * 2))
        self._feedback.set_delay_ns(half_period_ns)

    @property
    def active(self):
        return self.O.value == 1

    @classmethod
    def get_parameters(cls):
        return {
            "frequency": {
                "type": "int",
                "min": 1,
                "max": 50,
                "default": 1,
                "description": "Clock frequency in Hz",
                "reconfigurable": True,
            },
        }
