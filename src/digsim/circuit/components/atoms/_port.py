# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""This module contains the classes for all component ports"""

from __future__ import annotations

import abc
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, NoReturn

from ._digsim_exception import DigsimException


if TYPE_CHECKING:
    from ._component import Component


# A value: a number, undefined ("X"), or not driven, high impedance ("Z")
VALUE_TYPE = int | Literal["X", "Z"]


def resolve(values: list[VALUE_TYPE]) -> VALUE_TYPE:
    """
    The value of a wire with several drivers: the value of the ones that drive it (all
    but those that are "Z"), "Z" if none does, and "X" if they drive different values
    (contention) or one of them drives "X"
    """
    driven = [value for value in values if value != "Z"]
    if not driven:
        return "Z"
    first = driven[0]
    return first if all(value == first for value in driven) else "X"


class _Drivers:
    """
    The drivers of a port with more than one (see Port.wire). The port gets its
    value from all of them: set_value() of the port is replaced, and each driver that
    changes sets the value of them all (a driver has its new value before it sets its
    wires). Ports with one driver don't have this, so they work as fast as before.
    """

    def __init__(self, set_value: Callable[[VALUE_TYPE], None]) -> None:
        self.drivers: list[Port] = []
        self._set_value = set_value

    def set_value(self, value: VALUE_TYPE) -> None:
        self._set_value(resolve([driver.value for driver in self.drivers]))


class PortConnectionError(DigsimException):
    """Exception for illegal connections"""


class ConnectionGeneration:
    """
    A counter increased on every connection change, lets callers cache results that
    depend on the wiring. It is kept outside the Port class: changing a class
    attribute thousands of times (while wiring a large circuit) makes CPython stop
    optimizing attribute access on that class.
    """

    __slots__ = ("value",)

    def __init__(self) -> None:
        self.value = 0


connection_generation = ConnectionGeneration()


class Port(abc.ABC):
    """The abstract base class for all ports"""

    def __init__(self, parent: Component, name: str, width: int = 1, output: bool = False) -> None:
        self._parent = parent  # The parent component
        self._name: str = name  # The name of this port
        self._width: int = width  # The bit-width of this port
        self._output: bool = output  # Is this port an output port
        self._wired_ports: list[Port] = []  # The ports that this port drives
        self._value: VALUE_TYPE = "X"  # The value of this port
        self._edge_detect_value: VALUE_TYPE = "X"  # Last edge detect value
        self._tristate = False  # Can this port drive "Z", and share a wire with others
        self._drivers: _Drivers | None = None  # The drivers, if more than one
        self.init()  # Initialize the port

    def init(self) -> None:
        """Initialize port, will be called when the component/circuit is initialized"""
        self._value = "X"
        self._edge_detect_value = "X"
        self.update_wires("X")

    @property
    def wired_ports(self) -> list[Port]:
        """Get the ports that this port drives"""
        return self._wired_ports

    @property
    def value(self) -> VALUE_TYPE:
        """Get the value of the port, can be "X" """
        return self._value

    @value.setter
    def value(self, value: VALUE_TYPE) -> None:
        """Set the value of the port"""
        self.set_value(value)

    @property
    def width(self) -> int:
        """Get the bit-width of the port"""
        return self._width

    @property
    def wire(self) -> NoReturn:
        """Need a property if to be able to have a setter..."""
        raise PortConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port: Port) -> None:
        """
        Wire setter, connect this port to an input port (of same width). An input port can
        have several drivers: its value is the value they drive, "X" if they drive
        different values, and a tristate driver that drives "Z" doesn't count (see
        resolve()).
        """
        if self.width != port.width:
            raise PortConnectionError("Cannot connect ports with different widths")
        if port is self:
            raise PortConnectionError(f"Cannot connect {self.path()}.{self.name()} to itself")
        if port.has_driver():
            drivers = port.get_drivers()
            if self in drivers:
                raise PortConnectionError(
                    f"The port {port.path()}.{port.name()} is already connected"
                )
            port.add_driver(self)
        else:
            port.set_driver(self)
        self._wired_ports.append(port)
        connection_generation.value += 1
        port.value = self._value  # Update wires when port is connected

    def remove_wires(self) -> None:
        """Remove wires port"""
        for port in self._wired_ports:
            port.remove_driver(self)
        self._wired_ports = []
        connection_generation.value += 1

    def set_tristate(self, tristate: bool = True) -> None:
        """Let the port drive "Z" (high impedance), when it doesn't drive its wires"""
        self._tristate = tristate

    def is_tristate(self) -> bool:
        """Can the port drive "Z" (high impedance), when it doesn't drive its wires"""
        return self._tristate

    def get_drivers(self) -> list[Port]:
        """The ports that drive this port: none, one, or several"""
        if self._drivers is not None:
            return list(self._drivers.drivers)
        driver = self.get_driver()
        return [] if driver is None else [driver]

    def add_driver(self, port: Port) -> None:
        """Add one more driver to a port that has one"""
        if self._drivers is None:
            # From now on the port gets its value from all its drivers
            existing = self.get_drivers()
            self._drivers = _Drivers(self.set_value)
            self._drivers.drivers = existing
            self.set_value = self._drivers.set_value  # type: ignore[method-assign]
        self._drivers.drivers.append(port)

    def remove_driver(self, port: Port) -> None:
        """
        Remove a driver of the port, the others keep driving it. A port without drivers is
        "X", like a port that was never connected.
        """
        if self._drivers is None:
            self.set_driver(None)
            self.set_value("X")
            return
        if port in self._drivers.drivers:
            self._drivers.drivers.remove(port)
        drivers = self._drivers.drivers
        if len(drivers) < 2:
            # A port with one driver (or none) again, a new driver is checked against it
            del self.set_value
            self._drivers = None
        self.set_driver(drivers[0] if drivers else None)
        # The value of the drivers that are left
        self.set_value(drivers[0].value if drivers else "X")

    def name(self) -> str:
        """Get port name"""
        return self._name

    def path(self) -> str:
        """Get port path, <component_name>...<component_name>"""
        return self._parent.path()

    def parent(self) -> Component:
        """Get parent component"""
        return self._parent

    def update_wires(self, value: VALUE_TYPE) -> None:
        """Update connected wires (and self._value) with value"""
        if self._value == value:
            return
        self._value = value
        for port in self._wired_ports:
            port.set_value(value)

    def get_wired_ports_recursive(self, processed_ports: set[Port] | None = None) -> list[Port]:
        """Get all connected ports (iterative), avoiding duplicates."""
        if processed_ports is None:
            processed_ports = set()

        all_wired_ports: list[Port] = []
        ports_to_process: list[Port] = [self]

        while ports_to_process:
            port = ports_to_process.pop()
            if port in processed_ports:
                continue
            processed_ports.add(port)
            all_wired_ports.append(port)
            ports_to_process.extend(port.wired_ports)
        return all_wired_ports

    def is_output(self) -> bool:
        """Return True if this port is an output port"""
        return self._output

    def is_input(self) -> bool:
        """Return True if this port is an input port (or an inout port)"""
        return not self._output

    def is_inout(self) -> bool:
        """
        Return True if this port is bidirectional, an inout port: both an output and an
        input (see PortInOut)
        """
        return False

    def is_rising_edge(self) -> bool:
        """
        Return True if a rising edge has occurred
        Note: This function can only be called once per 'update'
        """
        rising_edge = False
        if self.value == 1 and self._edge_detect_value == 0:
            rising_edge = True
        self._edge_detect_value = self.value
        return rising_edge

    def is_falling_edge(self) -> bool:
        """
        Return True if a falling edge has occurred
        Note: This function can only be called once per 'update'
        """
        falling_edge = False
        if self.value == 0 and self._edge_detect_value == 1:
            falling_edge = True
        self._edge_detect_value = self.value
        return falling_edge

    @abc.abstractmethod
    def set_value(self, value: VALUE_TYPE) -> None:
        """Set value on port"""

    @abc.abstractmethod
    def set_driver(self, port: Port | None) -> None:
        """Set port driver"""

    @abc.abstractmethod
    def has_driver(self) -> bool:
        """Return True if port has driver"""

    def get_driver(self) -> Port | None:
        """Get port driver"""
        return None

    def can_add_wire(self) -> bool:
        """
        Return True if it is possible to add a wire to this port: always, an input port
        can have several drivers
        """
        return True

    def disconnect(self, port: Port) -> None:
        """Disconnect 'port' if this port drives it"""
        # Only then: the port could be driven by another port, that keeps its connection
        if port in self._wired_ports:
            self._wired_ports.remove(port)
            port.remove_driver(self)
            connection_generation.value += 1

    def strval(self) -> str:
        """Return value as string"""
        if isinstance(self.value, str):
            return self.value
        if self.width > 1:
            return f"0x{self.value:x}"
        return f"{self.value}"

    def __str__(self) -> str:
        return f"{self._parent.name()}:{self._name}={self.value}"


class PortWire(Port):
    """
    The PortWire class:
    * The port wire will instantaneously update the driven wires upon change.
    """

    def __init__(self, parent: Component, name: str, width: int = 1, output: bool = False) -> None:
        super().__init__(parent, name, width, output)
        self._port_driver: Port | None = None  # The port that drives this port

    def set_value(self, value: VALUE_TYPE) -> None:
        if value != self._value:
            self.update_wires(value)

    def set_driver(self, port: Port | None) -> None:
        self._port_driver = port

    def get_driver(self) -> Port | None:
        """Get driver for port"""
        return self._port_driver

    def has_driver(self) -> bool:
        """Return True if port has driver"""
        return self._port_driver is not None


class PortIn(PortWire):
    """
    The PortIn class:
    * The port wire will instantaneously update the driven wires upon change.
    * The port will update the parent component upon change.
    """

    def __init__(self, parent: Component, name: str, width: int = 1) -> None:
        super().__init__(parent, name, width, output=False)

    def set_value(self, value: VALUE_TYPE) -> None:
        # The same as PortWire.set_value(), inlined since it is called for every event
        if value != self._value:
            self.update_wires(value)
        self._parent.update()


class PortOutDelta(Port):
    """
    The PortOutDelta class:
    * The port wire will update the driven wires after a delta cycle.
    * The port will update the parent component if the _update_parent variable is set to true.
    """

    def __init__(self, parent: Component, name: str, width: int = 1, delay_ns: int = 1) -> None:
        super().__init__(parent, name, width, output=True)
        self._delay_ns = delay_ns  # Propagation delay for this port
        self._update_parent = False  # Should this port update parent on change
        # The circuit's add_event() (a component's circuit doesn't change), called for
        # every event without going through the component
        self._add_event = parent.circuit.add_event

    def update_parent(self, update_parent: bool) -> None:
        """Set if the port updates its parent when it changes"""
        self._update_parent = update_parent

    def set_delay_ns(self, delay_ns: int) -> None:
        """Set port propagation delay"""
        self._delay_ns = delay_ns

    def set_value(self, value: VALUE_TYPE) -> None:
        self._add_event(self, value, self._delay_ns)

    def update_port(self, value: VALUE_TYPE) -> None:
        """Update the port output and the connected wires"""
        self.update_wires(value)
        if self._update_parent:
            self._parent.update()

    def delta_cycle(self, value: VALUE_TYPE) -> None:
        """Handle the delta cycle event from the circuit"""
        # The same as update_port(), inlined since it is called for every event
        self.update_wires(value)
        if self._update_parent:
            self._parent.update()

    def set_driver(self, port: Port | None) -> NoReturn:
        raise PortConnectionError(f"The port {self.path()}.{self.name()} cannot be driven")

    def get_driver(self) -> Port | None:
        """Get driver for port, the output port has no driver"""
        return None

    def has_driver(self) -> bool:
        """Return False since the port does not have a driver"""
        return False


class PortOutImmediate(PortOutDelta):
    """
    The PortOutImmediate class:
    * A special version of the PortOutDelta used for direct components (button/switch/value)
    * The port driver will update the driven wires immediately
    * The port will update the parent component if the _update_parent variable is set to true.
    """

    def __init__(self, parent: Component, name: str, width: int = 1) -> None:
        super().__init__(parent, name, width)

    def set_value(self, value: VALUE_TYPE) -> None:
        self._add_event(self, value, 0)
        super().update_port(value)

    def delta_cycle(self, value: VALUE_TYPE) -> None:
        """
        Do nothing here, the event is just used to update waves in Circuit class
        """


class PortWireBit(PortWire):
    """
    The PortWireBit class is used when several bits should be collected into
    a multi bit bus port.
    The PortWireBit will update its parent (a PortMultiBitWire) upon change.
    """

    def __init__(
        self, parent: Component, name: str, parent_port: PortMultiBitWire, output: bool
    ) -> None:
        super().__init__(parent, name, 1, output)
        self._parent_port = parent_port

    def set_value(self, value: VALUE_TYPE) -> None:
        super().set_value(value)
        self._parent_port.update_value_from_bits()

    def get_parent_port(self) -> PortMultiBitWire:
        """Get the parent PortMultiBitWire for this port"""
        return self._parent_port


class PortMultiBitWire(Port):
    """
    The PortMultiBitWire class is used when several bits should be collected into
    a multi bit bus port.
    The PortMultiBitWire will add events to the circuit upon change to update vcd output.
    """

    def __init__(self, parent: Component, name: str, width: int, output: bool = False) -> None:
        self._port_driver: Port | None = None  # The port that drives this port
        self._bits: list[PortWireBit] = []
        super().__init__(parent, name, width, output)
        for bit_id in range(self.width):
            self._bits.append(
                PortWireBit(parent, f"{self.name()}_{bit_id}", self, output=not output)
            )

    def init(self) -> None:
        super().init()
        for bit in self._bits:
            bit.init()

    def set_value(self, value: VALUE_TYPE) -> None:
        if isinstance(value, str):
            # Undefined, or not driven: none of the bits is
            for bit in self._bits:
                bit.value = value
            return
        for bit_id, bit in enumerate(self._bits):
            bit_val = (value >> bit_id) & 1
            bit.value = bit_val

    def get_wired_ports_recursive(self, processed_ports: set[Port] | None = None) -> list[Port]:
        if processed_ports is None:
            processed_ports = set()

        all_wired_ports = super().get_wired_ports_recursive(processed_ports)
        for bit in self._bits:
            all_wired_ports.extend(bit.get_wired_ports_recursive(processed_ports))
        return all_wired_ports

    def set_driver(self, port: Port | None) -> None:
        """Set port driver"""
        self._port_driver = port

    def get_driver(self) -> Port | None:
        """Get port driver"""
        return self._port_driver

    def has_driver(self) -> bool:
        """Return True if port has driver"""
        return self._port_driver is not None

    def get_bit(self, bit_id: int) -> Port:
        """Get bit port"""
        return self._bits[bit_id]

    def update_value_from_bits(self) -> None:
        """Update the port with the value of the bits"""
        value = 0
        not_driven = 0
        for bit_id, bit in enumerate(self._bits):
            bit_value = bit.value
            if bit_value == "X":
                if self._value != "X":
                    self.update_wires("X")
                    # Send event just to update waves, also when the bus becomes undefined
                    self.parent().add_event(self, "X", 0)
                return
            if bit_value == "Z":
                not_driven += 1
                continue
            value = value | (bit_value << bit_id)
        if not_driven:
            # Not driven if no bit is, and undefined if only some are
            bus_value: VALUE_TYPE = "Z" if not_driven == len(self._bits) else "X"
            if self._value != bus_value:
                self.update_wires(bus_value)
                self.parent().add_event(self, bus_value, 0)
            return
        self.update_wires(value)
        # Send event just to update waves
        self.parent().add_event(self, value, 0)

    def delta_cycle(self, value: VALUE_TYPE) -> None:
        """
        Do nothing here, the event passed in 'update_value_from_bits'
        is just used to update waves in Circuit class
        """


def _bit(value: VALUE_TYPE, bit_id: int) -> VALUE_TYPE:
    """One bit of a value, "X" and "Z" are the same for every bit"""
    if isinstance(value, str):
        return value
    return (value >> bit_id) & 1


class _InOutDriveBit(PortWire):
    """A bit of what the component of an inout port drives on it, it updates the port"""

    def __init__(self, parent: Component, name: str, inout_port: PortInOut, bit_id: int) -> None:
        super().__init__(parent, name, 1, output=False)
        self._inout_port = inout_port
        self._bit_id = bit_id

    def drive(self) -> VALUE_TYPE:
        """What the bit drives: "Z" if nothing in the component drives it"""
        return self._value if self.has_driver() else "Z"

    def set_value(self, value: VALUE_TYPE) -> None:
        super().set_value(value)
        self._inout_port.drive_changed(self._bit_id)


class PortInOut(Port):
    """
    A bidirectional port of one or more bits, like an inout port of a Verilog module.

    Like an output, it drives the ports it is wired to with what its component drives on
    it, "Z" (not driven) while the component doesn't. Like an input, other ports can drive
    it. The component reads the value of the wire, at each bit what it drives itself
    resolved with what the other ports drive (see resolve()), and only that is "X" when
    they drive different values.

    The bits that the component drives are the drive bits, get_drive_bit(), and the bits
    it reads are get_bit(). The value of the port is what it drives, as for a tristate
    output, and read_value() is the value of the wire. A word of which only some bits are
    driven is "X" for the ports it drives.

    Two inout ports on the same wire drive each other: a.wire = b and b.wire = a.
    """

    def __init__(self, parent: Component, name: str, width: int = 1) -> None:
        self._port_driver: Port | None = None  # The first port that drives this port
        self._other_value: VALUE_TYPE = "Z"  # What the other ports drive on the wire
        self._drive_bits: list[_InOutDriveBit] = []
        self._read_bits: list[PortWire] = []
        super().__init__(parent, name, width, output=True)
        for bit_id in range(width):
            self._drive_bits.append(_InOutDriveBit(parent, f"{name}_drive_{bit_id}", self, bit_id))
            self._read_bits.append(PortWire(parent, f"{name}_{bit_id}", output=True))

    def init(self) -> None:
        super().init()
        self._other_value = "X" if self.has_driver() else "Z"
        for bit in [*self._drive_bits, *self._read_bits]:
            bit.init()
        # Bits that nothing in the component drives drive "Z" from the start, and the
        # ports the port drives get the value after their own init()
        drive = self._drive_word() if self._drive_bits else "X"
        if drive != "X":
            self._parent.add_event(self, drive, 0)

    def is_input(self) -> bool:
        """Return True, an inout port can be driven by other ports"""
        return True

    def is_inout(self) -> bool:
        """Return True, see Port.is_inout()"""
        return True

    def set_value(self, value: VALUE_TYPE) -> None:
        """
        Set what the other ports drive on the wire. A testbench can drive the port like
        this, "Z" to let go of the wire.
        """
        self._other_value = value
        for bit_id, bit in enumerate(self._read_bits):
            bit.set_value(self._read_bit(bit_id))

    def remove_driver(self, port: Port) -> None:
        """Remove a driver of the port, without drivers no other port drives the wire"""
        super().remove_driver(port)
        if not self.has_driver():
            self.set_value("Z")

    def _read_bit(self, bit_id: int) -> VALUE_TYPE:
        """The value of a bit of the wire, see resolve()"""
        drive = self._drive_bits[bit_id].drive()
        other = _bit(self._other_value, bit_id)
        if drive == "Z":
            return other
        if other in ("Z", drive):
            return drive
        return "X"

    def _drive_word(self) -> VALUE_TYPE:
        """What the component drives on the port, "X" if only some of the bits"""
        value = 0
        driven = 0
        for bit_id, bit in enumerate(self._drive_bits):
            bit_value = bit.drive()
            if bit_value == "X":
                return "X"
            if bit_value == "Z":
                continue
            driven += 1
            value |= bit_value << bit_id
        if not driven:
            return "Z"
        return value if driven == self.width else "X"

    def drive_changed(self, bit_id: int) -> None:
        """A drive bit changed: update the bit that the component reads, and the wires"""
        self._read_bits[bit_id].set_value(self._read_bit(bit_id))
        drive = self._drive_word()
        if drive != self._value:
            self.update_wires(drive)
            # Send event just to update waves
            self._parent.add_event(self, drive, 0)

    def read_value(self) -> VALUE_TYPE:
        """
        The value of the wire, what the port drives resolved with what the other ports
        drive: "X" if they drive different values, or only some bits of a word are driven
        """
        value = 0
        not_driven = 0
        for bit_id, bit in enumerate(self._read_bits):
            bit_value = bit.value
            if bit_value == "X":
                return "X"
            if bit_value == "Z":
                not_driven += 1
                continue
            value |= bit_value << bit_id
        if not_driven:
            return "Z" if not_driven == self.width else "X"
        return value

    def get_wired_ports_recursive(self, processed_ports: set[Port] | None = None) -> list[Port]:
        if processed_ports is None:
            processed_ports = set()
        all_wired_ports = super().get_wired_ports_recursive(processed_ports)
        for bit in self._read_bits:
            all_wired_ports.extend(bit.get_wired_ports_recursive(processed_ports))
        return all_wired_ports

    def set_driver(self, port: Port | None) -> None:
        """Set port driver"""
        self._port_driver = port

    def get_driver(self) -> Port | None:
        """Get port driver"""
        return self._port_driver

    def has_driver(self) -> bool:
        """Return True if port has driver"""
        return self._port_driver is not None

    def get_bit(self, bit_id: int) -> Port:
        """The bit of the wire that the component reads, it drives the ports of the component"""
        return self._read_bits[bit_id]

    def get_drive_bit(self, bit_id: int) -> Port:
        """The bit that the component drives, ports of the component are wired to it"""
        return self._drive_bits[bit_id]

    def delta_cycle(self, value: VALUE_TYPE) -> None:
        """Drive the wires after init(), the other events only update waves"""
        self.update_wires(value)
