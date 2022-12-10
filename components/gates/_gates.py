from components import Component, InputPort, OutputPort, SignalLevel


class NOT(Component):
    def __init__(self, name="NOT"):
        super().__init__(name)
        self._in = InputPort(self)
        self._out = OutputPort(self)
        self.add_port("I", self._in)
        self.add_port("O", self._out)

    def update(self):
        if self._in.level == SignalLevel.LOW:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW


class AND(Component):
    def __init__(self, name="AND"):
        super().__init__(name)
        self._ina = InputPort(self)
        self._inb = InputPort(self)
        self._out = OutputPort(self)

        self.add_port("A", self._ina)
        self.add_port("B", self._inb)
        self.add_port("O", self._out)

    def update(self):
        if self._ina.level == SignalLevel.HIGH and self._inb.level == SignalLevel.HIGH:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW


class NAND(Component):
    def __init__(self, name="NAND"):
        super().__init__(name)
        self._and = AND(f"{name}_AND")
        self._not = NOT(f"{name}_NOT")
        self._and.outport("O").connect(self._not.inport("I"))

        self.add_port("A", self._and.inport("A"))
        self.add_port("B", self._and.inport("B"))
        self.add_port("O", self._not.outport("O"))


class SR(Component):
    def __init__(self, name="SR"):
        super().__init__(name)
        self._nands = NAND(f"{name}_NANDS")
        self._nandr = NAND(f"{name}_NANDR")
        self._nands.outport("O").connect(self._nandr.inport("A"))
        self._nandr.outport("O").connect(self._nands.inport("B"))

        self.add_port("nS", self._nands.inport("A"))
        self.add_port("nR", self._nandr.inport("B"))
        self.add_port("Q", self._nands.outport("O"))
        self.add_port("nQ", self._nandr.outport("O"))
