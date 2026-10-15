# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the LED component"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .atoms import CallbackComponent, Component, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class Led(CallbackComponent):
    """
    An LED, lit while its input is 1.

    Ports:
        I: Input.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        callback: Called with the component when its input changes.
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        callback: Callable[[Component], None] | None = None,
    ) -> None:
        super().__init__(circuit, name, callback)
        self.add_port(PortIn(self, "I"))

    @property
    def active(self) -> bool:
        return self.I.has_driver() and self.I.value == 1
