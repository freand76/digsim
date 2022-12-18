from components import (Component, InputFanOutPort, InputPort, MultiComponent,
                        OutputPort, SignalLevel)


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
        self._ina = InputPort(self)
        self._inb = InputPort(self)
        self._out = OutputPort(self)

        self.add_port("A", self._ina)
        self.add_port("B", self._inb)
        self.add_port("Y", self._out)

    def update(self):
        if self._ina.level == SignalLevel.HIGH and self._inb.level == SignalLevel.HIGH:
            self._out.level = SignalLevel.LOW
        else:
            self._out.level = SignalLevel.HIGH


class NAND3(Component):
    def __init__(self, circuit, name="NAND3"):
        super().__init__(circuit, name)
        self._ina = InputPort(self)
        self._inb = InputPort(self)
        self._inc = InputPort(self)
        self._out = OutputPort(self)

        self.add_port("A", self._ina)
        self.add_port("B", self._inb)
        self.add_port("C", self._inc)
        self.add_port("Y", self._out)

    def update(self):
        if (
            self._ina.level == SignalLevel.HIGH
            and self._inb.level == SignalLevel.HIGH
            and self._inc.level == SignalLevel.HIGH
        ):
            self._out.level = SignalLevel.LOW
        else:
            self._out.level = SignalLevel.HIGH


class SR(MultiComponent):
    def __init__(self, circuit, name="SR"):
        super().__init__(circuit, name)
        _nands = NAND(circuit, f"{name}_S")
        _nandr = NAND(circuit, f"{name}_R")
        _nands.outport("Y").connect(_nandr.inport("A"))
        _nandr.outport("Y").connect(_nands.inport("B"))

        self.add_port("nS", _nands.inport("A"))
        self.add_port("nR", _nandr.inport("B"))
        self.add_port("Q", _nands.outport("Y"))
        self.add_port("nQ", _nandr.outport("Y"))


class JK_MS(MultiComponent):
    def __init__(self, circuit, name="JK"):
        super().__init__(circuit, name)

        notclk = NOT(circuit, f"{name}_NOT_CLK")
        mnandj = NAND3(circuit, f"{name}_M_J")
        mnandk = NAND3(circuit, f"{name}_M_K")
        master = SR(circuit, f"{name}_SR_M")

        snandj = NAND(circuit, f"{name}_S_J")
        snandk = NAND(circuit, f"{name}_S_K")
        slave = SR(circuit, f"{name}_SR_S")

        inc = InputFanOutPort(self)
        inc.connect(mnandj.inport("A"))
        inc.connect(mnandk.inport("A"))
        inc.connect(notclk.inport("A"))
        self.add_port("C", inc)

        mnandj.outport("Y").connect(master.inport("nS"))
        mnandk.outport("Y").connect(master.inport("nR"))
        master.outport("Q").connect(snandj.inport("A"))
        master.outport("nQ").connect(snandk.inport("A"))
        notclk.outport("Y").connect(snandj.inport("B"))
        notclk.outport("Y").connect(snandk.inport("B"))
        snandj.outport("Y").connect(slave.inport("nS"))
        snandk.outport("Y").connect(slave.inport("nR"))
        slave.outport("Q").connect(mnandk.inport("B"))
        slave.outport("nQ").connect(mnandj.inport("B"))

        self.add_port("J", mnandj.inport("C"))
        self.add_port("K", mnandk.inport("C"))
        self.add_port("Q", slave.outport("Q"))


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

    def update(self):
        if self._inr.level == SignalLevel.HIGH:
            self._out.level = SignalLevel.LOW
        elif (
            self._inc.level != self._old_inc_level
            and self._inc.level == SignalLevel.HIGH
            and self._ine.level == SignalLevel.HIGH
        ):
            self._out.level = self._ind.level

        self._old_inc_level = self._inc.level
