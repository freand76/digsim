# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with 7-segment LED component"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING

from .atoms import CallbackComponent, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class SevenSegment(CallbackComponent):
    """
    A 7-segment display, with an input for each segment.

    Ports:
        A, B, ..., G: Inputs, one for each segment.
        dot: Input for the decimal point.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

    PORTLIST: typing.ClassVar = ["A", "B", "C", "D", "E", "F", "G", "dot"]

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        for portname in self.PORTLIST:
            self.add_port(PortIn(self, portname))

    def segments(self) -> str:
        """Get the active segments"""
        segments = ""
        for portname in self.PORTLIST:
            if self.port(portname).value == 1:
                if portname == "dot":
                    segments += "."
                else:
                    segments += portname
        return segments
