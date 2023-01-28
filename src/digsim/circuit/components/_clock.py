# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Clock component module """

from .atoms import CallbackComponent, PortOut


class Clock(CallbackComponent):
    """Clock component class"""

    def __init__(self, circuit, frequency=1, name="Clock"):
        super().__init__(circuit, name)
        self._portout = PortOut(self, "O")
        self._portout.update_parent(True)
        self.add_port(self._portout)
        self._frequency = None
        self.set_frequency(frequency)

    def init(self):
        super().init()
        self.add_event(self.O, value=0, delay_ns=0)

    def update(self):
        if self.O.value == 1:
            self.O.value = 0
        else:
            self.O.value = 1
        super().update()

    def set_frequency(self, frequency):
        """Set the clock frequency in hertz"""
        self._frequency = frequency
        half_period_ns = int(1000000000 / (frequency * 2))
        self._portout.set_delay_ns(half_period_ns)

    @property
    def active(self):
        return self._portout.value == 1

    def setup(self, frequency=None):
        """Setup from settings"""
        if frequency is not None:
            self.set_frequency(frequency)

    def settings_to_dict(self):
        return {"frequency": self._frequency}
