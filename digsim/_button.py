# pylint: disable=no-member

from ._component import Component
from ._port import ComponentPort, PortDirection, SignalLevel


class PushButton(Component):
    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        self._inverted = inverted
        self.add_port(ComponentPort(self, "O", PortDirection.OUT))

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
