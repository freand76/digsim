# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with flip flops and latches"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import Component, PortIn, PortOutDelta, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class FlipFlop(Component):
    """FlipFlip factory component"""

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "name": {
                "type": "component_name",
                "component_list": {
                    "SRFF": "SR FlipFlop",
                    "ClockedSRFF": "SR FlipFlop (Edge triggered)",
                    "ClockedJKFF": "JK FlipFlop (Edge triggered)",
                    "ClockedTFF": "T FlipFlop (Edge triggered)",
                },
                "description": "Select flip-flop",
            }
        }


class SRFF(Component):
    """SR-FlipFlop"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name, display_name="SR")
        self.add_port(PortIn(self, "S"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortOutDelta(self, "Q"))

    def update(self) -> None:
        if self.S.value == 1:
            self.Q.value = 1
        if self.R.value == 1:
            self.Q.value = 0


class ClockedJKFF(Component):
    """Clocked JK-FlipFlop"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name, display_name="JK-FlipFlop")
        self.add_port(PortWire(self, "J"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "K"))
        self.add_port(PortOutDelta(self, "Q"))

    def update(self) -> None:
        rising_edge = self.C.is_rising_edge()
        if rising_edge:
            if self.J.value == 1 and self.K.value == 1:
                self.Q.value = 1 if self.Q.value == 0 else 0
            elif self.J.value == 1:
                self.Q.value = 1
            elif self.K.value == 1:
                self.Q.value = 0


class ClockedSRFF(Component):
    """Clocked SR-FlipFlop"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name, display_name="SR-FlipFlop")
        self.add_port(PortWire(self, "S"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "R"))
        self.add_port(PortOutDelta(self, "Q"))

    def update(self) -> None:
        rising_edge = self.C.is_rising_edge()
        if rising_edge:
            if self.S.value == 1:
                self.Q.value = 1
            if self.R.value == 1:
                self.Q.value = 0


class ClockedTFF(Component):
    """Clocked T-FlipFlop"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name, display_name="T-FlipFlop")
        self.add_port(PortWire(self, "T"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortOutDelta(self, "Q"))

    def init(self) -> None:
        self.T.value = 0

    def update(self) -> None:
        rising_edge = self.C.is_rising_edge()
        if rising_edge and self.T.value == 1:
            self.Q.value = 1 if self.Q.value == 0 else 0
