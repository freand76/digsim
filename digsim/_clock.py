# pylint: disable=no-member

from ._component import Component
from ._port import ComponentPort, OutputPort, PortDirection, SignalLevel


class Clock(Component):
    def __init__(self, circuit, frequency, name="Clock"):
        super().__init__(circuit, name)
        self.add_port(OutputPort(self, "O", propagation_delay_ns=0))
        self._feedback_out = OutputPort(self, "FO")
        self._feedback_in = ComponentPort(self, "FI", PortDirection.IN)
        self._feedback_out.wire = self._feedback_in
        self._feedback_out.wire = self.O
        self.set_frequency(frequency)

    def init(self):
        self._feedback_out.level = SignalLevel.HIGH
        self.O.level = SignalLevel.LOW

    def update(self):
        if self._feedback_in.level == SignalLevel.HIGH:
            self._feedback_out.level = SignalLevel.LOW
        else:
            self._feedback_out.level = SignalLevel.HIGH

    def set_frequency(self, frequency):
        half_period_ns = int(1000000000 / (frequency * 2))
        self._feedback_out.set_propagation_delay_ns(half_period_ns)

    @property
    def wire(self):
        raise ConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port
