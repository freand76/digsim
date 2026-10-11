# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A PushButton component"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import CallbackComponent, PortOutImmediate


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class PushButton(CallbackComponent):
    """PushButton component class"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        portout = PortOutImmediate(self, "O")
        self.add_port(portout)
        portout.update_parent(True)

    def default_state(self) -> None:
        self.release()

    def push(self) -> None:
        """Push pushbutton"""
        self.O.value = 1

    def release(self) -> None:
        """Release pushbutton"""
        self.O.value = 0

    def reconfigure(self) -> None:
        self.release()

    @property
    def has_action(self) -> bool:
        return True

    @property
    def active(self) -> bool:
        return self.O.value == 1

    def onpress(self) -> None:
        self.push()

    def onrelease(self) -> None:
        self.release()
