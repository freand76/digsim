from components import (Component, InputPort, MultiComponent, OutputPort,
                        SignalLevel)


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
        _nands = NAND(circuit, name=f"{name}_S")
        _nandr = NAND(circuit, name=f"{name}_R")
        self.add(_nands)
        self.add(_nandr)
        _nands.Y.wire = _nandr.A
        _nandr.Y.wire = _nands.B

        self.add_port("nS", InputPort(self))
        self.add_port("nR", InputPort(self))
        self.add_port("Q", InputPort(self))
        self.add_port("nQ", InputPort(self))

        self.nS.wire = _nands.A
        self.nR.wire = _nandr.B
        _nands.Y.wire = self.Q
        _nandr.Y.wire = self.nQ


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

        self.add_port("C", InputPort(self))
        self.add_port("J", InputPort(self))
        self.add_port("K", InputPort(self))
        self.add_port("Q", InputPort(self))

        self.J.wire = mnandj.C
        self.K.wire = mnandk.C
        slave.Q.wire = self.Q

        self.C.wire = mnandj.A
        self.C.wire = mnandk.A
        self.C.wire = notclk.A

        mnandj.Y.wire = master.nS
        mnandk.Y.wire = master.nR
        master.Q.wire = snandj.A
        master.nQ.wire = snandk.A
        notclk.Y.wire = snandj.B
        notclk.Y.wire = snandk.B
        snandj.Y.wire = slave.nS
        snandk.Y.wire = slave.nR
        slave.Q.wire = mnandk.B
        slave.nQ.wire = mnandj.B


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
