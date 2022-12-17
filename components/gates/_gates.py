from components import Component, InputPort, OutputPort, SignalLevel


class NOT(Component):
    def __init__(self, circuit, name="NOT"):
        super().__init__(circuit, name)
        self._in = InputPort(self)
        self._out = OutputPort(self)
        self.add_port("A", self._in)
        self.add_port("Y", self._out)

    def update(self):
        if self._in.level == SignalLevel.LOW:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW


class AND(Component):
    def __init__(self, circuit, name="AND"):
        super().__init__(circuit, name)
        self._ina = InputPort(self)
        self._inb = InputPort(self)
        self._out = OutputPort(self)

        self.add_port("A", self._ina)
        self.add_port("B", self._inb)
        self.add_port("Y", self._out)

    def update(self):
        if self._ina.level == SignalLevel.HIGH and self._inb.level == SignalLevel.HIGH:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW


class XOR(Component):
    def __init__(self, circuit, name="XOR"):
        super().__init__(circuit, name)
        self._ina = InputPort(self)
        self._inb = InputPort(self)
        self._out = OutputPort(self)

        self.add_port("A", self._ina)
        self.add_port("B", self._inb)
        self.add_port("Y", self._out)

    def update(self):
        if (
            self._ina.level == SignalLevel.HIGH and self._inb.level == SignalLevel.LOW
        ) or (
            self._ina.level == SignalLevel.LOW and self._inb.level == SignalLevel.HIGH
        ):
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW


class NAND(Component):
    def __init__(self, circuit, name="NAND"):
        super().__init__(circuit, name)
        self._and = AND(f"{name}_AND")
        self._not = NOT(f"{name}_NOT")
        self._and.outport("Y").connect(self._not.inport("A"))

        self.add_port("A", self._and.inport("A"))
        self.add_port("B", self._and.inport("B"))
        self.add_port("Y", self._not.outport("Y"))


class SR(Component):
    def __init__(self, circuit, name="SR"):
        super().__init__(circuit, name)
        self._nands = NAND(circuit, f"{name}_NANDS")
        self._nandr = NAND(circuit, f"{name}_NANDR")
        self._nands.outport("Y").connect(self._nandr.inport("A"))
        self._nandr.outport("Y").connect(self._nands.inport("B"))

        self.add_port("nS", self._nands.inport("A"))
        self.add_port("nR", self._nandr.inport("B"))
        self.add_port("Q", self._nands.outport("Y"))
        self.add_port("nQ", self._nandr.outport("Y"))


class DFFE_PP0P(Component):
    def __init__(self, circuit, name="DFFE"):
        super().__init__(circuit, name)
        self._inc = InputPort(self)
        self._ind = InputPort(self, update_parent=False)
        self._ine = InputPort(self, update_parent=False)
        self._inr = InputPort(self)
        self._out = OutputPort(self)

        self.add_port("C", self._inc)
        self.add_port("D", self._ind)
        self.add_port("E", self._ine)
        self.add_port("R", self._inr)
        self.add_port("Q", self._out)
        self._old_inc_level = self._inc.level
        self._next_q_level = SignalLevel.LOW

    def update(self):
        if self._inr.level == SignalLevel.HIGH:
            self._out.level = SignalLevel.LOW
        elif (
            self._inc.level != self._old_inc_level
            and self._inc.level == SignalLevel.HIGH
            and self._ine.level == SignalLevel.HIGH
        ):
            self._next_q_level = self._ind.level

        self._old_inc_level = self._inc.level

    def delta(self):
        self._out.level = self._next_q_level
