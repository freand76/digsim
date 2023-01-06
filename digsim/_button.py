# pylint: disable=no-member

from ._component import CallbackComponent
from ._port import ComponentPort, OutputPort, PortDirection, SignalLevel


class PushButton(CallbackComponent):
    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        self._inverted = inverted
        self.add_port(OutputPort(self, "O", propagation_delay_ns=10))
        self._feedback_in = ComponentPort(self, "FI", PortDirection.IN)
        self.O.wire = self._feedback_in

    def init(self):
        super().init()
        self.release()

    def push(self):
        if self._inverted:
            self.O.level = SignalLevel.LOW
        else:
            self.O.level = SignalLevel.HIGH

    def release(self):
        if self._inverted:
            self.O.level = SignalLevel.HIGH
        else:
            self.O.level = SignalLevel.LOW

    @property
    def has_action(self):
        return True

    @property
    def active(self):
        if self._inverted:
            return self.O.level == SignalLevel.LOW
        return self.O.level == SignalLevel.HIGH

    def onpress(self):
        self.push()

    def onrelease(self):
        self.release()
