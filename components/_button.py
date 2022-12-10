from components import Component, OutputPort, SignalLevel


class PushButton(Component):
    def __init__(self, name="PushButton", inverted=False):
        super().__init__(name)
        self._inverted = inverted
        self._out = OutputPort(self)
        self.add_port("O", self._out)

    def init(self):
        self.release()

    def push(self):
        print(f"{self.name} PUSH")
        if self._inverted:
            self._out.level = SignalLevel.LOW
        else:
            self._out.level = SignalLevel.HIGH

    def release(self):
        print(f"{self.name} RELEASE")
        if self._inverted:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW

    def push_release(self):
        self.push()
        self.release()
