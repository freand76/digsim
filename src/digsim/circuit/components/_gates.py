# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Module with the basic logic gates """

from .atoms import Component, MultiComponent, PortIn, PortOut, PortWire


class NOT(Component):
    """NOT logic gate"""

    def __init__(self, circuit, name="NOT"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortOut(self, "Y"))

    def update(self):
        if self.A.value == 0:
            self.Y.value = 1
        elif self.A.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = "X"


class OR(Component):
    """OR logic gate"""

    def __init__(self, circuit, name="OR"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOut(self, "Y"))

    def update(self):
        if self.A.value == 0 and self.B.value == 0:
            self.Y.value = 0
        elif 1 in (self.A.value, self.B.value):
            self.Y.value = 1
        else:
            self.Y.value = "X"


class AND(Component):
    """AND logic gate"""

    def __init__(self, circuit, name="AND"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOut(self, "Y"))

    def update(self):
        if self.A.value == 1 and self.B.value == 1:
            self.Y.value = 1
        elif 0 in (self.A.value, self.B.value):
            self.Y.value = 0
        else:
            self.Y.value = "X"


class XOR(Component):
    """XOR logic gate"""

    def __init__(self, circuit, name="XOR"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOut(self, "Y"))

    def update(self):
        if (self.A.value == 1 and self.B.value == 0) or (self.A.value == 0 and self.B.value == 1):
            self.Y.value = 1
        elif (self.A.value == 1 and self.B.value == 1) or (
            self.A.value == 0 and self.B.value == 0
        ):
            self.Y.value = 0
        else:
            self.Y.value = "X"


class NAND(Component):
    """NAND logic gate"""

    def __init__(self, circuit, name="NAND"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOut(self, "Y"))

    def update(self):
        if self.A.value == 1 and self.B.value == 1:
            self.Y.value = 0
        elif 0 in (self.A.value, self.B.value):
            self.Y.value = 1
        else:
            self.Y.value = "X"


class NOR(Component):
    """NOR logic gate"""

    def __init__(self, circuit, name="NOR"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOut(self, "Y"))

    def update(self):
        if self.A.value == 0 and self.B.value == 0:
            self.Y.value = 1
        elif 1 in (self.A.value, self.B.value):
            self.Y.value = 0
        else:
            self.Y.value = "X"


class DFF(Component):
    """D-FlipFlop"""

    def __init__(self, circuit, name="NOR"):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortOut(self, "Q"))

    def update(self):
        if self.C.is_rising_edge():
            self.Q.value = self.D.value


class SR(MultiComponent):
    """SR logic gate composed of two NAND gates"""

    def __init__(self, circuit, name="SR"):
        super().__init__(circuit, name)
        _nands = NAND(circuit, name=f"{name}_S")
        _nandr = NAND(circuit, name=f"{name}_R")
        self.add(_nands)
        self.add(_nandr)
        _nands.Y.wire = _nandr.A
        _nandr.Y.wire = _nands.B
        self.add_port(PortWire(self, "nS"))
        self.add_port(PortWire(self, "nR"))
        self.add_port(PortWire(self, "Q"))
        self.add_port(PortWire(self, "nQ"))

        self.nS.wire = _nands.A
        self.nR.wire = _nandr.B
        _nands.Y.wire = self.Q
        _nandr.Y.wire = self.nQ
