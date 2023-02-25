# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Clock component module """

from .atoms import CallbackComponent, PortOut


class Clock(CallbackComponent):
    """Clock component class"""

    def __init__(self, circuit, name="Clock", frequency=1):
        super().__init__(circuit, name)
        self._portout = PortOut(self, "O")
        self._portout.update_parent(True)
        self.add_port(self._portout)
        self.parameter_set("frequency", frequency)
        self.reconfigure()

    def init(self):
        super().init()
        self.add_event(self.O, value=0, delay_ns=0)

    def update(self):
        if self.O.value == 1:
            self.O.value = 0
        else:
            self.O.value = 1
        super().update()

    def reconfigure(self):
        frequency = self.parameter_get("frequency")
        half_period_ns = int(1000000000 / (frequency * 2))
        self._portout.set_delay_ns(half_period_ns)

    @property
    def active(self):
        return self._portout.value == 1

    @classmethod
    def get_parameters(cls):
        return {
            "frequency": {
                "type": int,
                "min": 1,
                "max": 50,
                "default": 1,
                "description": "Clock frequency in Hz",
                "reconfigurable": True,
            },
        }
