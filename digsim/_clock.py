# pylint: disable=no-member

from ._component import CallbackComponent
from ._port import ComponentPort, OutputPort, PortDirection, SignalLevel


class Clock(CallbackComponent):
    def __init__(self, circuit, frequency, name="Clock"):
        super().__init__(circuit, name)
        self._clock_port = OutputPort(
            self, "Clock", propagation_delay_ns=0, update_parent_on_delta=True
        )
        self.add_port(ComponentPort(self, "O", PortDirection.OUT))
        self._clock_port.wire = self.O
        self.set_frequency(frequency)

    def init(self):
        super().init()
        self.O.level = SignalLevel.LOW
        self._clock_port.level = SignalLevel.HIGH

    def update(self):
        if self._clock_port.level == SignalLevel.HIGH:
            self._clock_port.level = SignalLevel.LOW
        else:
            self._clock_port.level = SignalLevel.HIGH
        super().update()

    def set_frequency(self, frequency):
        half_period_ns = int(1000000000 / (frequency * 2))
        self._clock_port.set_propagation_delay_ns(half_period_ns)

    @property
    def active(self):
        return self.O.level == SignalLevel.HIGH

    @property
    def wire(self):
        raise ConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port
