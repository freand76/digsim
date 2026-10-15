# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Components that only exist in the model"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import Component


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class Note(Component):
    """
    A text note in the GUI. It has no ports.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        text: The text.
    """

    def __init__(self, circuit: Circuit, name: str | None = None, text: str = "") -> None:
        super().__init__(circuit, name)
        self.parameter_set("text", text)

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return {
            "text": {
                "type": "str",
                "default": "Write something here...",
                "description": "Note text",
                "reconfigurable": True,
            },
        }
