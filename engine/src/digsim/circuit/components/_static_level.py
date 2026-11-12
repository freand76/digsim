# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Static Logic components"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class VDD(Component):
    """
    A constant logic 1.

    Ports:
        O: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "O", delay_ns=0))

    def default_state(self) -> None:
        self.O.value = 1


class GND(Component):
    """
    A constant logic 0.

    Ports:
        O: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "O", delay_ns=0))

    def default_state(self) -> None:
        self.O.value = 0
