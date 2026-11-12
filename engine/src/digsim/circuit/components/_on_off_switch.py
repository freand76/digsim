# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""An On/Off Switch  component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import CallbackComponent, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class OnOffSwitch(CallbackComponent):
    """
    A switch that stays on or off. Its output is 1 while it is on.

    Ports:
        O: Output.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
    """

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        portout = PortOutDelta(self, "O", delay_ns=0)
        self.add_port(portout)
        portout.update_parent(True)
        self._on = False

    def _set(self, state: bool) -> None:
        self._on = state
        self.O.value = 1 if state else 0

    def default_state(self) -> None:
        self._set(False)

    def turn_on(self) -> None:
        """Turn on the switch"""
        self._set(True)

    def turn_off(self) -> None:
        """Turn off the switch"""
        self._set(False)

    def toggle(self) -> None:
        """Toggle the switch"""
        self._set(not self._on)

    def onpress(self) -> None:
        self.toggle()

    @property
    def has_action(self) -> bool:
        return True

    @property
    def active(self) -> bool:
        return self._on
