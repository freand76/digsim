# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Probe component module"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import VALUE_TYPE, CallbackComponent, ComponentException, Parameter, PortIn


if TYPE_CHECKING:
    from digsim.circuit import Circuit

PROBE_RADIXES = ["hex", "dec", "bin"]


class Probe(CallbackComponent):
    """
    Shows the value of a wire or a bus, in the GUI. In Python, its value is `I.value`, or
    `text()` for the value as the GUI shows it.

    Ports:
        I: Input, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of bits, 1 to 32.
        radix: How the value is shown: "hex", "dec" or "bin".
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, width: int = 1, radix: str = "hex"
    ) -> None:
        super().__init__(circuit, name)
        if radix not in PROBE_RADIXES:
            raise ComponentException(f"Unknown radix '{radix}', use one of {PROBE_RADIXES}")
        self.add_port(PortIn(self, "I", width=width))
        self.parameter_set("width", width)
        self.parameter_set("radix", radix)

    def text(self, value: VALUE_TYPE | None = None) -> str:
        """
        The value of the input (or 'value') as text, in the radix of the probe, with all
        digits for the width. "X" (undefined) and "Z" (not driven) as they are.
        """
        if value is None:
            value = self.I.value
        if not isinstance(value, int):
            return str(value)
        width = self.I.width
        radix = self.parameter_get("radix")
        if radix == "bin" or width == 1:
            return f"{value:0{width}b}"
        if radix == "dec":
            return str(value)
        return f"{value:0{(width + 3) // 4}X}"

    def widest_text(self) -> str:
        """The widest text the probe shows, for its size in the GUI"""
        widest = self.text((1 << self.I.width) - 1)
        if self.parameter_get("radix") == "dec":
            # Not all digits are as wide
            widest = "8" * len(widest)
        return widest

    def reconfigure(self) -> None:
        # The new radix is shown
        self.update()

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "width": {
                "type": "int",
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bus width",
            },
            "radix": {
                "type": "list",
                "items": PROBE_RADIXES,
                "default": "hex",
                "description": "Show the value as",
                "reconfigurable": True,
            },
        }
