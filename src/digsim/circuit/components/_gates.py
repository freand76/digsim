# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Module with the basic logic gates """

import math

from .atoms import Component, ComponentException, MultiComponent, PortIn, PortOut, PortWire


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


class ConfigPortsComponent(Component):
    """Base class for components with configurable input ports"""

    def __init__(self, circuit, name, ports):
        super().__init__(circuit, name)
        self._inports = []
        portname = "A"
        for _ in range(ports):
            port = PortIn(self, portname)
            self._inports.append(port)
            self.add_port(port)
            portname = chr(ord(portname) + 1)
        self.add_port(PortOut(self, "Y"))

    @classmethod
    def get_parameters(cls):
        return {
            "ports": {
                "type": int,
                "min": 2,
                "max": 8,
                "default": 2,
                "description": "Number of input ports",
            },
        }

    def settings_to_dict(self):
        return {"ports": len(self._inports)}


class OR(ConfigPortsComponent):
    """OR logic gate"""

    def __init__(self, circuit, name="OR", ports=2):
        super().__init__(circuit, name, ports)

    def update(self):
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        elif any(port.value == 1 for port in self._inports):
            self.Y.value = 1
        else:
            self.Y.value = 0


class AND(ConfigPortsComponent):
    """AND logic gate"""

    def __init__(self, circuit, name="AND", ports=2):
        super().__init__(circuit, name, ports)

    def update(self):
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        elif all(port.value == 1 for port in self._inports):
            self.Y.value = 1
        else:
            self.Y.value = 0


class XOR(ConfigPortsComponent):
    """XOR logic gate"""

    def __init__(self, circuit, name="XOR", ports=2):
        super().__init__(circuit, name, ports)

    def update(self):
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        else:
            count = 0
            for port in self._inports:
                count += port.value
            self.Y.value = count % 2


class NAND(ConfigPortsComponent):
    """NAND logic gate"""

    def __init__(self, circuit, name="NAND", ports=2):
        super().__init__(circuit, name, ports)

    def update(self):
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        elif all(port.value == 1 for port in self._inports):
            self.Y.value = 0
        else:
            self.Y.value = 1


class NOR(ConfigPortsComponent):
    """NOR logic gate"""

    def __init__(self, circuit, name="OR", ports=2):
        super().__init__(circuit, name, ports)

    def update(self):
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        elif any(port.value == 1 for port in self._inports):
            self.Y.value = 0
        else:
            self.Y.value = 1


class DFF(Component):
    """D-FlipFlop"""

    def __init__(self, circuit, name="DFF", width=1):
        super().__init__(circuit, name)
        self.add_port(PortWire(self, "D", width=width))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortOut(self, "Q", width=width))

    def update(self):
        if self.C.is_rising_edge():
            self.Q.value = self.D.value

    @classmethod
    def get_parameters(cls):
        return {
            "width": {
                "type": int,
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bitwidth of D and Q ports",
            },
        }

    def settings_to_dict(self):
        return {"width": self.D.width}


class MUX(Component):
    """MUX"""

    def __init__(self, circuit, name, ports=2, width=1):
        super().__init__(circuit, name)
        if ports not in [2, 4, 8]:
            raise ComponentException(f"Mux cannot have {ports} number of ports")
        self._inports = []
        portname = "A"
        for _ in range(ports):
            port = PortIn(self, portname, width=width)
            self._inports.append(port)
            self.add_port(port)
            portname = chr(ord(portname) + 1)
        self.add_port(PortIn(self, "S", width=int(math.log2(ports))))
        self.add_port(PortOut(self, "Y", width=width))

    def update(self):
        if self.S.value == "X":
            return
        self.Y.value = self._inports[self.S.value].value

    @classmethod
    def get_parameters(cls):
        return {
            "ports": {
                "type": "intrange",
                "range": [2, 4, 8],
                "default_index": 0,
                "description": "Number of input ports",
            },
            "width": {
                "type": int,
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bitwidth of mux ports",
            },
        }

    def settings_to_dict(self):
        return {"ports": len(self._inports), "width": self.A.width}


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
