from components import ActorComponent, OutputPort, SignalLevel


class PushButton(ActorComponent):
    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        self._inverted = inverted
        self._out = OutputPort(self)
        self.add_port("O", self._out)

    def init(self):
        self.release()

    def push(self):
        if self._inverted:
            self._out.level = SignalLevel.LOW
        else:
            self._out.level = SignalLevel.HIGH
        self.actor_event()

    def release(self):
        if self._inverted:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW
        self.actor_event()

    def push_release(self, count=1):
        for _ in range(count):
            self.push()
            self.release()
