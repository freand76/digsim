# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""This module contains the classes for all component ports"""

from __future__ import annotations

import abc
from typing import Literal, Optional, Union

from ._digsim_exception import DigsimException


VALUE_TYPE = Union[int, Literal["X"]]


class PortConnectionError(DigsimException):
    """Exception for illegal connections"""


class Port(abc.ABC):
    """The abstract base class for all ports"""

    def __init__(self, parent, name: str, width: int = 1, output: bool = False):
        self._parent = parent  # The parent component
        self._name: str = name  # The name of this port
        self._width: int = width  # The bit-width of this port
        self._output: bool = output  # Is this port an output port
        self._wired_ports: list[Port] = []  # The ports that this port drives
        self._value: VALUE_TYPE = "X"  # The value of this port
        self._edge_detect_value: VALUE_TYPE = "X"  # Last edge detect value
        self.init()  # Initialize the port

    def init(self):
        """Initialize port, will be called when compponent/circuit is initialized"""
        self._value = "X"
        self._edge_detect_value = "X"
        self.update_wires("X")

    @property
    def wired_ports(self) -> list[Port]:
        """Get wires from thisport"""
        return self._wired_ports

    @property
    def value(self) -> VALUE_TYPE:
        """Get the value of the port, can be "X" """
        return self._value

    @value.setter
    def value(self, value: VALUE_TYPE):
        """Set the value of the port"""
        self.set_value(value)

    @property
    def width(self) -> int:
        """Get the bit-width of the port"""
        return self._width

    @width.setter
    def width(self, width: int):
        """Set the bit-width of the port, will force a disconnect if it is connected"""
        if width != self._width:
            driver = self.get_driver()
            if driver is not None:
                driver.disconnect(self)
            for port in self._wired_ports[:]:
                self.disconnect(port)
        self._width = width

    @property
    def wire(self):
        """Need a property if to be able to have a setter..."""
        raise PortConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port: PortWire):
        """Wire setter, connect this port to an input port (of same width)"""
        if port.has_driver():
            raise PortConnectionError(f"The port {port.path()}.{port.name()} already has a driver")
        if self.width != port.width:
            raise PortConnectionError("Cannot connect ports with different widths")
        port.set_driver(self)
        self._wired_ports.append(port)
        port.value = self._value  # Update wires when port is connected

    def remove_wires(self):
        """Remove wires port"""
        for port in self._wired_ports:
            port.set_driver(None)
        self._wired_ports = []

    def name(self) -> str:
        """Get port name"""
        return self._name

    def path(self) -> str:
        """Get port path, <component_name>...<component_name>"""
        return self._parent.path()

    def parent(self):
        """Get parent component"""
        return self._parent

    def update_wires(self, value: VALUE_TYPE):
        """Update connected wires (and self._value) with value"""
        if self._value == value:
            return
        self._value = value
        for port in self._wired_ports:
            port.value = self._value

    def get_wired_ports_recursive(self, processed_ports: Optional[set] = None) -> list[Port]:
        """Get all connected ports (iterative), avoiding duplicates."""
        if processed_ports is None:
            processed_ports = set()

        all_wired_ports = []
        ports_to_process = [self]

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
        """Return True if this port is an input port"""
        return not self._output

    def is_rising_edge(self) -> bool:
        """
        Return True if a rising edge has occured
        Note: This function can only be called once per 'update'
        """
        rising_edge = False
        if self.value == 1 and self._edge_detect_value == 0:
            rising_edge = True
        self._edge_detect_value = self.value
        return rising_edge

    def is_falling_edge(self) -> bool:
        """
        Return True if a falling edge has occured
        Note: This function can only be called once per 'update'
        """
        falling_edge = False
        if self.value == 0 and self._edge_detect_value == 1:
            falling_edge = True
        self._edge_detect_value = self.value
        return falling_edge

    @abc.abstractmethod
    def set_value(self, value: VALUE_TYPE):
        """Set value on port"""

    @abc.abstractmethod
    def set_driver(self, port: Port | None):
        """Set port driver"""

    @abc.abstractmethod
    def has_driver(self) -> bool:
        """Return True if port has driver"""

    def get_driver(self):
        """Get port driver"""

    def can_add_wire(self) -> bool:
        """Return True if it is possible to add a wire to this port"""
        if self.is_output():
            return True
        if not self.has_driver():
            return True
        return False

    def disconnect(self, port: Port):
        """Disconnect port if it is wired"""
        if port in self._wired_ports:
            index = self._wired_ports.index(port)
            del self._wired_ports[index]
        port.set_driver(None)

    def strval(self) -> str:
        """Return value as string"""
        if self.value == "X":
            return "X"
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

    def __init__(self, parent, name: str, width: int = 1, output: bool = False):
        super().__init__(parent, name, width, output)
        self._port_driver: Port | None = None  # The port that drives this port

    def set_value(self, value: VALUE_TYPE):
        if value != self.value:
            self.update_wires(value)

    def set_driver(self, port: Port | None):
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

    def __init__(self, parent, name: str, width: int = 1):
        super().__init__(parent, name, width, output=False)

    def set_value(self, value: VALUE_TYPE):
        super().set_value(value)
        self.parent().update()


class PortOutDelta(Port):
    """
    The PortOutDelta class:
    * The port wire will update the driven wires after a delta cycle.
    * The port will update the parent component if the _update_parent variable is set to true.
    """

    def __init__(self, parent, name: str, width: int = 1, delay_ns: int = 1):
        super().__init__(parent, name, width, output=True)
        self._delay_ns = delay_ns  # Propagation delay for this port
        self._update_parent = False  # Should this port update parent on change

    def update_parent(self, update_parent: bool):
        """Set update parent valiable (True/False)"""
        self._update_parent = update_parent

    def set_delay_ns(self, delay_ns: int):
        """Set port propagation delay"""
        self._delay_ns = delay_ns

    def set_value(self, value: VALUE_TYPE):
        self.parent().add_event(self, value, self._delay_ns)

    def update_port(self, value: VALUE_TYPE):
        """Update the port output and the connected wires"""
        self.update_wires(value)
        if self._update_parent:
            self.parent().update()

    def delta_cycle(self, value: VALUE_TYPE):
        """Handle the delta cycle event from the circuit"""
        self.update_port(value)

    def set_driver(self, port: Port | None):
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

    def __init__(self, parent, name: str, width: int = 1):
        super().__init__(parent, name, width)

    def set_value(self, value: VALUE_TYPE):
        self.parent().add_event(self, value, 0)
        super().update_port(value)

    def delta_cycle(self, value: VALUE_TYPE):
        """
        Do nothing here, the event is just used to updates waves in Circuit class
        """


class PortWireBit(PortWire):
    """
    The PortWireBit class is used when several bits should be collected into
    a multi bit bus port.
    The PortWireBit will update its parent (a PortMultiBitWire) upon change.
    """

    def __init__(self, parent, name: str, parent_port: PortMultiBitWire, output: bool):
        super().__init__(parent, name, 1, output)
        self._parent_port = parent_port

    def set_value(self, value: VALUE_TYPE):
        super().set_value(value)
        self._parent_port.update_value_from_bits()

    def get_parent_port(self) -> PortMultiBitWire:
        """Get the parent PortMultiBitWire for this port"""
        return self._parent_port


class PortMultiBitWire(Port):
    """
    The PortMultiWireBit class is used when several bits should be collected into
    a multi bit bus port.
    The PortWireMultiBit will add events to the circuit upon change to update vcd output.
    """

    def __init__(self, parent, name: str, width: int, output: bool = False):
        self._port_driver: Port | None = None  # The port that drives this port
        self._bits = []
        super().__init__(parent, name, width, output)
        for bit_id in range(self.width):
            self._bits.append(
                PortWireBit(parent, f"{self.name()}_{bit_id}", self, output=not output)
            )

    def init(self):
        super().init()
        for bit in self._bits:
            bit.init()

    def set_value(self, value: VALUE_TYPE):
        if isinstance(value, str):
            return
        for bit_id, bit in enumerate(self._bits):
            bit_val = (value >> bit_id) & 1
            bit.value = bit_val

    def get_wired_ports_recursive(self, processed_ports: Optional[set] = None) -> list[Port]:
        if processed_ports is None:
            processed_ports = set()

        all_wired_ports = super().get_wired_ports_recursive(processed_ports)
        for bit in self._bits:
            all_wired_ports.extend(bit.get_wired_ports_recursive(processed_ports))
        return all_wired_ports

    def set_driver(self, port: Port | None):
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

    def update_value_from_bits(self):
        """Update the port with the value of the bits"""
        value = 0
        for bit_id, bit in enumerate(self._bits):
            if bit.value == "X":
                self.update_wires("X")
                return
            value = value | (bit.value << bit_id)
        self.update_wires(value)
        # Send event just to update waves
        self.parent().add_event(self, value, 0)

    def delta_cycle(self, value: VALUE_TYPE):
        """
        Do nothing here, the event passed in 'update_value_from_bits'
        is just used to updates waves in Circuit class
        """
