# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import CallbackComponent, OutputPort, SignalLevel, WireConnectionError


class Clock(CallbackComponent):
    def __init__(self, circuit, frequency=1, name="Clock"):
        super().__init__(circuit, name)
        self.add_port(
            OutputPort(
                self,
                "O",
                update_parent_on_delta=True,
                default_level=SignalLevel.LOW,
            )
        )
        self._frequency = None
        self.set_frequency(frequency)

    def init(self):
        super().init()
        self.add_event(self.O, SignalLevel.LOW, 0)

    def update(self):
        if self.O.level == SignalLevel.HIGH:
            self.O.level = SignalLevel.LOW
        else:
            self.O.level = SignalLevel.HIGH
        super().update()

    def set_frequency(self, frequency):
        self._frequency = frequency
        half_period_ns = int(1000000000 / (frequency * 2))
        self.O.set_propagation_delay_ns(half_period_ns)

    @property
    def active(self):
        return self.O.level == SignalLevel.HIGH

    @property
    def wire(self):
        raise WireConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port

    def settings_from_dict(self, settings):
        if "frequency" in settings:
            self.set_frequency(settings["frequency"])

    def settings_to_dict(self):
        return {"frequency": self._frequency}
