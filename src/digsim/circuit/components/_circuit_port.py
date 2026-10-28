# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The ports of a circuit: its inputs, outputs and inout ports, its interface"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from .atoms import (
    VALUE_TYPE,
    CallbackComponent,
    ComponentException,
    Parameter,
    PortIn,
    PortInOut,
    PortOutDelta,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit

MAX_WIDTH = 32


def circuit_ports(circuit: Circuit) -> list[CircuitPort]:
    """The circuit ports of a circuit (not of its subcircuits), in the order they were added"""
    return [
        component
        for component in circuit.get_toplevel_components()
        if isinstance(component, CircuitPort)
    ]


def _free_label(base: str, taken: list[str]) -> str:
    """The base name, or with a number (in2, in3, ...) if it is taken"""
    if base not in taken:
        return base
    number = 2
    while f"{base}{number}" in taken:
        number += 1
    return f"{base}{number}"


class CircuitPort(CallbackComponent):
    """
    The base class of the circuit ports, named by their label. The labels are unique in a
    circuit, a subcircuit of it gets a port with each label.
    """

    # "in", "out" or "inout"
    DIRECTION: ClassVar[str] = ""
    # The label of a new port, with a number when it is taken
    DEFAULT_LABEL: ClassVar[str] = ""

    def __init__(self, circuit: Circuit, name: str | None, label: str, width: int) -> None:
        # Checked before the component is added to the circuit
        if not label.isidentifier():
            raise ComponentException(f"The circuit port name '{label}' is not a name")
        if label in [port.label() for port in circuit_ports(circuit)]:
            raise ComponentException(f"The circuit has a port '{label}' already")
        if not 1 <= width <= MAX_WIDTH:
            raise ComponentException(f"The width must be 1 to {MAX_WIDTH}")
        super().__init__(circuit, name)
        self._label = label
        self._width = width
        self.parameter_set("label", label)
        self.parameter_set("width", width)

    def label(self) -> str:
        """The name of the port"""
        return self._label

    @property
    def width(self) -> int:
        """The number of bits"""
        return self._width

    @property
    def value(self) -> VALUE_TYPE:
        """The value of the port, see the classes of the ports"""
        raise NotImplementedError

    @classmethod
    def _port_parameters(cls, labels: list[str]) -> dict[str, Parameter]:
        return {
            "label": {
                "type": "str",
                "single_line": True,
                "default": _free_label(cls.DEFAULT_LABEL, labels),
                "description": "Port name",
                "invalid_list": labels,
            },
            "width": {
                "type": "int",
                "min": 1,
                "max": MAX_WIDTH,
                "default": 1,
                "description": "Bitwidth of the port",
            },
        }

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return cls._port_parameters([])

    @classmethod
    def get_circuit_parameters(cls, circuit: Circuit) -> dict[str, Parameter]:
        return cls._port_parameters([port.label() for port in circuit_ports(circuit)])


class CircuitInput(CircuitPort):
    """
    An input of the circuit. In the circuit itself it drives a value, 0 at the start, that
    set_value() sets. In a subcircuit, its input with the label takes its place.

    Ports:
        <label>: Output, named like the label, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        label: The name of the port.
        width: The number of bits, 1 to 32.
    """

    DIRECTION = "in"
    DEFAULT_LABEL = "in"

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "in", width: int = 1
    ) -> None:
        super().__init__(circuit, name, label, width)
        self._value = 0
        self._output = PortOutDelta(self, label, width=width, delay_ns=0)
        self._output.update_parent(True)
        self.add_port(self._output)

    def default_state(self) -> None:
        self._value = 0
        self._output.value = 0

    def set_value(self, value: int) -> None:
        """
        Drive a value.

        Args:
            value: The value, 0 to 2^width - 1.
        """
        if not 0 <= value < 1 << self._width:
            raise ComponentException(f"{value} does not fit in {self._width} bits")
        self._value = value
        self._output.value = value

    @property
    def value(self) -> int:
        """The value it drives"""
        return self._value

    def onpress(self) -> None:
        # A 1-bit input toggles, like a switch
        if self._width == 1:
            self.set_value(1 - self._value)

    @property
    def has_action(self) -> bool:
        return self._width == 1

    @property
    def active(self) -> bool:
        return self._value != 0


class CircuitOutput(CircuitPort):
    """
    An output of the circuit, it shows the value of its input. In a subcircuit, its output
    with the label takes its place.

    Ports:
        <label>: Input, named like the label, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        label: The name of the port.
        width: The number of bits, 1 to 32.
    """

    DIRECTION = "out"
    DEFAULT_LABEL = "out"

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "out", width: int = 1
    ) -> None:
        super().__init__(circuit, name, label, width)
        self._input = PortIn(self, label, width=width)
        self.add_port(self._input)

    @property
    def value(self) -> VALUE_TYPE:
        """The value of the input"""
        return self._input.value

    @property
    def active(self) -> bool:
        return self._input.value not in (0, "X", "Z")


class CircuitInOut(CircuitPort):
    """
    An inout port of the circuit: it shows the value of its wire, and drives a value that
    set_value() sets, or nothing ("Z") as at the start. In a subcircuit, its inout port with
    the label takes its place.

    Ports:
        <label>: Inout port, named like the label, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        label: The name of the port.
        width: The number of bits, 1 to 32.
    """

    DIRECTION = "inout"
    DEFAULT_LABEL = "io"

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "io", width: int = 1
    ) -> None:
        super().__init__(circuit, name, label, width)
        self._value: VALUE_TYPE = "Z"
        self._inout = PortInOut(self, label, width=width)
        self._inout.set_tristate()
        self.add_port(self._inout)
        # A driver for each bit of the port, and an input for each bit it reads, that
        # updates the component (for the GUI)
        self._drivers: list[PortOutDelta] = []
        self._readers: list[PortIn] = []
        for bit_id in range(width):
            driver = PortOutDelta(self, f"{label}_driver_{bit_id}", delay_ns=0)
            driver.set_tristate()
            driver.wire = self._inout.get_drive_bit(bit_id)
            self._drivers.append(driver)
            reader = PortIn(self, f"{label}_reader_{bit_id}")
            self._inout.get_bit(bit_id).wire = reader
            self._readers.append(reader)

    def init(self) -> None:
        super().init()
        for port in [*self._drivers, *self._readers]:
            port.init()

    def default_state(self) -> None:
        self._drive("Z")

    def _drive(self, value: VALUE_TYPE) -> None:
        self._value = value
        for bit_id, driver in enumerate(self._drivers):
            driver.value = (value >> bit_id) & 1 if isinstance(value, int) else value

    def set_value(self, value: int | str) -> None:
        """
        Drive a value on the wire, or nothing ("Z").

        Args:
            value: The value, 0 to 2^width - 1, or "Z".
        """
        if value != "Z" and not (isinstance(value, int) and 0 <= value < 1 << self._width):
            raise ComponentException(f"{value} does not fit in {self._width} bits")
        self._drive(value if isinstance(value, int) else "Z")

    @property
    def drive(self) -> VALUE_TYPE:
        """The value it drives, "Z" when it doesn't"""
        return self._value

    @property
    def value(self) -> VALUE_TYPE:
        """The value of the wire, what it drives resolved with what the others drive"""
        return self._inout.read_value()

    @property
    def active(self) -> bool:
        return self.value not in (0, "X", "Z")
