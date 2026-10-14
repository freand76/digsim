# Copyright (c) Fredrik Andersson, 2023-2024
# All rights reserved

"""Module with the basic logic gates"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from .atoms import Component, ComponentException, MultiComponent, PortIn, PortOutDelta, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class NOT(Component):
    """NOT logic gate"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self) -> None:
        if self.A.value == 0:
            self.Y.value = 1
        elif self.A.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = "X"


class ConfigPortsComponent(Component):
    """Base class for components with configurable input ports"""

    def __init__(self, circuit: Circuit, name: str | None, ports: int) -> None:
        super().__init__(circuit, name)
        self._inports: list[PortIn] = []
        portname = "A"
        for _ in range(ports):
            port = PortIn(self, portname)
            self._inports.append(port)
            self.add_port(port)
            portname = chr(ord(portname) + 1)
        self.add_port(PortOutDelta(self, "Y"))
        self.parameter_set("ports", ports)

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "ports": {
                "type": "int",
                "min": 2,
                "max": 8,
                "default": 2,
                "description": "Number of input ports",
            },
        }


class OR(ConfigPortsComponent):
    """OR logic gate"""

    def __init__(self, circuit: Circuit, name: str | None = None, ports: int = 2) -> None:
        super().__init__(circuit, name, ports)

    def update(self) -> None:
        if any(port.value == 1 for port in self._inports):
            self.Y.value = 1
        elif all(port.value == 0 for port in self._inports):
            self.Y.value = 0
        else:
            self.Y.value = "X"


class AND(ConfigPortsComponent):
    """AND logic gate"""

    def __init__(self, circuit: Circuit, name: str | None = None, ports: int = 2) -> None:
        super().__init__(circuit, name, ports)

    def update(self) -> None:
        if all(port.value == 1 for port in self._inports):
            self.Y.value = 1
        elif any(port.value == 0 for port in self._inports):
            self.Y.value = 0
        else:
            self.Y.value = "X"


class XOR(ConfigPortsComponent):
    """XOR logic gate"""

    def __init__(self, circuit: Circuit, name: str | None = None, ports: int = 2) -> None:
        super().__init__(circuit, name, ports)

    def update(self) -> None:
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        else:
            count = 0
            for port in self._inports:
                value = port.value
                assert value != "X"
                count += value
            self.Y.value = count % 2


class XNOR(ConfigPortsComponent):
    """XNOR logic gate, high when an even number of inputs are high"""

    def __init__(self, circuit: Circuit, name: str | None = None, ports: int = 2) -> None:
        super().__init__(circuit, name, ports)

    def update(self) -> None:
        if any(port.value == "X" for port in self._inports):
            self.Y.value = "X"
        else:
            count = 0
            for port in self._inports:
                value = port.value
                assert value != "X"
                count += value
            self.Y.value = 1 - count % 2


class NAND(ConfigPortsComponent):
    """NAND logic gate"""

    def __init__(self, circuit: Circuit, name: str | None = None, ports: int = 2) -> None:
        super().__init__(circuit, name, ports)

    def update(self) -> None:
        if all(port.value == 1 for port in self._inports):
            self.Y.value = 0
        elif any(port.value == 0 for port in self._inports):
            self.Y.value = 1
        else:
            self.Y.value = "X"


class NOR(ConfigPortsComponent):
    """NOR logic gate"""

    def __init__(self, circuit: Circuit, name: str | None = None, ports: int = 2) -> None:
        super().__init__(circuit, name, ports)

    def update(self) -> None:
        if any(port.value == 1 for port in self._inports):
            self.Y.value = 0
        elif all(port.value == 0 for port in self._inports):
            self.Y.value = 1
        else:
            self.Y.value = "X"


class DFF(Component):
    """D-FlipFlop"""

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        async_reset: bool = False,
        clock_enable: bool = False,
        width: int = 1,
    ) -> None:
        super().__init__(circuit, name)
        self._async_reset = async_reset
        self._clock_enable = clock_enable
        self.add_port(PortWire(self, "D", width=width))
        if self._async_reset:
            self.add_port(PortIn(self, "R"))
        if self._clock_enable:
            self.add_port(PortWire(self, "E"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortOutDelta(self, "Q", width=width))
        self.parameter_set("width", width)
        self.parameter_set("async_reset", async_reset)
        self.parameter_set("clock_enable", clock_enable)

    def update(self) -> None:
        rising_edge = self.C.is_rising_edge()
        if self._async_reset and self.R.value == 1:
            self.Q.value = 0
        elif rising_edge:
            if self._clock_enable and self.E.value == 0:
                # No clock enable
                return
            self.Q.value = self.D.value

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "async_reset": {
                "type": "bool",
                "default": False,
                "description": "Use asynchronous reset",
            },
            "clock_enable": {
                "type": "bool",
                "default": False,
                "description": "Use clock enable",
            },
            "width": {
                "type": "int",
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bitwidth of D and Q ports",
            },
        }


class MUX(Component):
    """MUX"""

    def __init__(
        self, circuit: Circuit, name: str | None = None, ports: int = 2, width: int = 1
    ) -> None:
        super().__init__(circuit, name)
        if ports not in [2, 4, 8]:
            raise ComponentException(f"Mux cannot have {ports} number of ports")
        self._inports: list[PortIn] = []
        portname = "A"
        for _ in range(ports):
            port = PortIn(self, portname, width=width)
            self._inports.append(port)
            self.add_port(port)
            portname = chr(ord(portname) + 1)
        self.add_port(PortIn(self, "S", width=int(math.log2(ports))))
        self.add_port(PortOutDelta(self, "Y", width=width))
        self.parameter_set("ports", ports)
        self.parameter_set("width", width)

    def update(self) -> None:
        select = self.S.value
        if select == "X":
            self.Y.value = "X"
            return
        self.Y.value = self._inports[select].value

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "ports": {
                "type": "intrange",
                "range": [2, 4, 8],
                "default_index": 0,
                "description": "Number of input ports",
            },
            "width": {
                "type": "int",
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bitwidth of mux ports",
            },
        }


class SR(MultiComponent):
    """SR latch composed of two NOR gates"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        _nands = NOR(circuit)
        _nandr = NOR(circuit)
        self.add(_nands)
        self.add(_nandr)
        _nands.Y.wire = _nandr.A
        _nandr.Y.wire = _nands.B
        self.add_port(PortWire(self, "S"))
        self.add_port(PortWire(self, "R"))
        self.add_port(PortWire(self, "Q", output=True))
        self.add_port(PortWire(self, "nQ", output=True))

        self.S.wire = _nands.A
        self.R.wire = _nandr.B
        _nands.Y.wire = self.nQ
        _nandr.Y.wire = self.Q
