from ._component import CallbackComponent
from ._port import ComponentPort, PortDirection, SignalLevel


class OnOffSwitch(CallbackComponent):
    def __init__(self, circuit, name="OnOffSwitch", start_on=False):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "O", PortDirection.OUT))
        self._on = False
        self._start_on = start_on

    def _set(self, on):
        if on:
            self.on()
        else:
            self.off()

    def init(self):
        self._set(self._start_on)

    def on(self):
        self.O.level = SignalLevel.HIGH
        self._on = True

    def off(self):
        self.O.level = SignalLevel.LOW
        self._on = False

    def toggle(self):
        self._set(not self._on)

    def onpress(self):
        self.toggle()
