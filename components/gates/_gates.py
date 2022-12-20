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


class AND_NOT(MultiComponent):
    def __init__(self, circuit, name="AND_NOT"):
        super().__init__(circuit, name)
        _and = AND(circuit, name=f"{name}_AND")
        _not = NOT(circuit, name=f"{name}_NOT")
        self.add(_and)
        self.add(_not)
        _and.port("Y").connect(_not.port("A"))

        self.add_port("A", InputFanOutPort(self))
        self.add_port("B", InputFanOutPort(self))
        self.add_port("Y", InputFanOutPort(self))

        self.port("A").connect(_and.port("A"))
        self.port("B").connect(_and.port("B"))
        _not.port("Y").connect(self.port("Y"))


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
        _nands = AND_NOT(circuit, name=f"{name}_S")
        _nandr = AND_NOT(circuit, name=f"{name}_R")
        self.add(_nands)
        self.add(_nandr)
        _nands.port("Y").connect(_nandr.port("A"))
        _nandr.port("Y").connect(_nands.port("B"))

        self.add_port("nS", InputFanOutPort(self))
        self.add_port("nR", InputFanOutPort(self))
        self.add_port("Q", InputFanOutPort(self))
        self.add_port("nQ", InputFanOutPort(self))

        self.port("nS").connect(_nands.port("A"))
        self.port("nR").connect(_nandr.port("B"))
        _nands.port("Y").connect(self.port("Q"))
        _nandr.port("Y").connect(self.port("nQ"))


class JK_MS(MultiComponent):
    def __init__(self, circuit, name="JK"):
        super().__init__(circuit, name)

        notclk = NOT(circuit, name=f"{name}_NOT_CLK")
        mnandj = NAND3(circuit, name=f"{name}_M_J")
        mnandk = NAND3(circuit, name=f"{name}_M_K")
        master = SR(circuit, name=f"{name}_SR_M")

        snandj = NAND(circuit, name=f"{name}_S_J")
        snandk = NAND(circuit, name=f"{name}_S_K")
        slave = SR(circuit, name=f"{name}_SR_S")

        self.add_port("C", InputFanOutPort(self))
        self.add_port("J", InputFanOutPort(self))
        self.add_port("K", InputFanOutPort(self))
        self.add_port("Q", InputFanOutPort(self))

        self.port("J").connect(mnandj.port("C"))
        self.port("K").connect(mnandk.port("C"))
        slave.port("Q").connect(self.port("Q"))

        self.port("C").connect(mnandj.port("A"))
        self.port("C").connect(mnandk.port("A"))
        self.port("C").connect(notclk.port("A"))

        mnandj.port("Y").connect(master.port("nS"))
        mnandk.port("Y").connect(master.port("nR"))
        master.port("Q").connect(snandj.port("A"))
        master.port("nQ").connect(snandk.port("A"))
        notclk.port("Y").connect(snandj.port("B"))
        notclk.port("Y").connect(snandk.port("B"))
        snandj.port("Y").connect(slave.port("nS"))
        snandk.port("Y").connect(slave.port("nR"))
        slave.port("Q").connect(mnandk.port("B"))
        slave.port("nQ").connect(mnandj.port("B"))


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
