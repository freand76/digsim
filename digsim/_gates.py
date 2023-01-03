from ._component import Component, MultiComponent
from ._port import ComponentPort, OutputPort, PortDirection, SignalLevel


class NOT(Component):
    def __init__(self, circuit, name="NOT"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.LOW:
            self.Y.level = SignalLevel.HIGH
        elif self.A.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.UNKNOWN


class AND(Component):
    def __init__(self, circuit, name="AND"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.HIGH
        elif SignalLevel.LOW in (self.A.level, self.B.level):
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.UNKNOWN


class NOT_AND(MultiComponent):
    def __init__(self, circuit, name="SR"):
        super().__init__(circuit, name)
        self._not = NOT(circuit, name=f"{name}_NOT")
        self._and = AND(circuit, name=f"{name}_AND")
        self.add(self._and)
        self.add(self._not)
        self._and.Y.wire = self._not.A
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(ComponentPort(self, "Y", PortDirection.OUT))

        self._not.Y.wire = self.Y
        self.A.wire = self._and.A
        self.B.wire = self._and.B


class XOR(Component):
    def __init__(self, circuit, name="XOR"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if (self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.LOW) or (
            self.A.level == SignalLevel.LOW and self.B.level == SignalLevel.HIGH
        ):
            self.Y.level = SignalLevel.HIGH
        elif (
            self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.HIGH
        ) or (self.A.level == SignalLevel.LOW and self.B.level == SignalLevel.LOW):
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.UNKNOWN


class NAND(Component):
    def __init__(self, circuit, name="NAND"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.LOW
        elif SignalLevel.LOW in (self.A.level, self.B.level):
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.UNKNOWN


class NAND3(Component):
    def __init__(self, circuit, name="NAND3"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if (
            self.A.level == SignalLevel.HIGH
            and self.B.level == SignalLevel.HIGH
            and self.C.level == SignalLevel.HIGH
        ):
            self.Y.level = SignalLevel.LOW
        elif SignalLevel.LOW in (self.A.level, self.B.level, self.C.level):
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.UNKNOWN


class SR(MultiComponent):
    def __init__(self, circuit, name="SR"):
        super().__init__(circuit, name)
        _nands = NAND(circuit, name=f"{name}_S")
        _nandr = NAND(circuit, name=f"{name}_R")
        self.add(_nands)
        self.add(_nandr)
        _nands.Y.wire = _nandr.A
        _nandr.Y.wire = _nands.B
        _nands.Y.level = SignalLevel.HIGH
        _nandr.Y.level = SignalLevel.HIGH
        self.add_port(ComponentPort(self, "nS", PortDirection.IN))
        self.add_port(ComponentPort(self, "nR", PortDirection.IN))
        self.add_port(ComponentPort(self, "Q", PortDirection.OUT))
        self.add_port(ComponentPort(self, "nQ", PortDirection.OUT))

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

        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "J", PortDirection.IN))
        self.add_port(ComponentPort(self, "K", PortDirection.IN))
        self.add_port(ComponentPort(self, "Q", PortDirection.IN))

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
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "E", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "R", PortDirection.IN))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.R.level == SignalLevel.HIGH:
            self.Q.level = SignalLevel.LOW
        elif (
            self.C.level != self._old_C_level
            and self.C.level == SignalLevel.HIGH
            and self.E.level == SignalLevel.HIGH
        ):
            self.Q.level = self.D.level

        self._old_C_level = self.C.level
