# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Static Logic components"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class VDD(Component):
    """VDD / Logic1 component class"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "O", delay_ns=0))

    def default_state(self) -> None:
        self.O.value = 1


class GND(Component):
    """GND / Logic0 component class"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "O", delay_ns=0))

    def default_state(self) -> None:
        self.O.value = 0
