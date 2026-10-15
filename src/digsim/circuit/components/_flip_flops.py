# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with flip flops and latches"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import Component, PortIn, PortOutDelta, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class FlipFlop(Component):
    """
    Lets the GUI choose a flip-flop type. In Python, create SRFF, ClockedSRFF, ClockedJKFF or
    ClockedTFF directly.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

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
    """
    An SR flip-flop: S sets Q to 1 and R resets it to 0, without a clock. R wins when both are 1.

    Ports:
        S: Set input.
        R: Reset input.
        Q: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

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
    """
    A JK flip-flop: on a rising clock edge, J sets Q to 1, K resets it to 0, and both toggle it.

    Ports:
        J: Input.
        C: Clock input.
        K: Input.
        Q: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

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
    """
    A clocked SR flip-flop: on a rising clock edge, S sets Q to 1 and R resets it to 0.
    R wins when both are 1.

    Ports:
        S: Set input.
        C: Clock input.
        R: Reset input.
        Q: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

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
    """
    A T flip-flop: Q toggles on a rising clock edge while T is 1.

    Ports:
        T: Input.
        C: Clock input.
        Q: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name, display_name="T-FlipFlop")
        self.add_port(PortWire(self, "T"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortOutDelta(self, "Q"))

    def init(self) -> None:
        super().init()
        self.T.value = 0

    def update(self) -> None:
        rising_edge = self.C.is_rising_edge()
        if rising_edge and self.T.value == 1:
            self.Q.value = 1 if self.Q.value == 0 else 0
