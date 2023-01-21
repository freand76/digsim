# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import abc


class PortConnectionError(Exception):
    """Exception for illegal connections"""


class Port(abc.ABC):
    def __init__(self, parent, name, width=1, output=False):
        self._parent = parent  # The parent component
        self._name = name  # The name of this port
        self._width = width  # The bit-width of this port
        self._output = output  # Is this port an output port
        self._wired_ports = []  # The ports that this port drives
        self._value = None  # The value of this port
        self.init()  # Initialize the port

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self.set_value(value)

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width != self._width:
            driver = self.get_driver()
            if driver is not None:
                driver.disconnect(self)
            for port in self._wired_ports:
                self.disconnect(port)
        self._width = width

    @property
    def wire(self):
        raise PortConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        if port.has_driver():
            raise PortConnectionError(f"The port {port.path()}.{port.name()} already has a driver")
        if self.width != port.width:
            raise PortConnectionError("Cannot connect ports with different widths")
        port.set_driver(self)
        self._wired_ports.append(port)
        port.value = self._value  # Update wires when port is connected

    def init(self):
        self._value = "X"

    def name(self):
        return self._name

    def path(self):
        return self._parent.path()

    def parent(self):
        return self._parent

    def update_wires(self, value):
        if self._value == value:
            return
        self._value = value
        for port in self._wired_ports:
            port.value = self._value

    def get_wires(self):
        return self._wired_ports

    def is_output(self):
        return self._output

    def is_input(self):
        return not self._output

    @abc.abstractmethod
    def set_value(self, value):
        pass

    @abc.abstractmethod
    def set_driver(self, port):
        pass

    def can_add_wire(self):
        if self.is_output():
            return True
        if not self.has_driver():
            return True
        return False

    def disconnect(self, port):
        index = self._wired_ports.index(port)
        del self._wired_ports[index]
        port.set_driver(None)

    def strval(self):
        if self.value == "X":
            return "X"
        if self.width > 1:
            return f"0x{self.value:x}"
        return f"{self.value}"

    def __str__(self):
        return f"{self._parent.name()}:{self._name}={self.value}"

    def to_dict_list(self):
        port_conn_list = []
        for port in self._wired_ports:
            # Only add port on top-level components
            if port.parent().is_toplevel():
                port_conn_list.append(
                    {
                        "src": f"{self.parent().name()}.{self.name()}",
                        "dst": f"{port.parent().name()}.{port.name()}",
                    }
                )
        return port_conn_list


class PortWire(Port):
    def __init__(self, parent, name, width=1, output=False):
        super().__init__(parent, name, width, output)
        self._port_driver = None  # The port that drives this port

    def set_value(self, value):
        if value != self.value:
            self.update_wires(value)

    def set_driver(self, port):
        self._port_driver = port

    def get_driver(self):
        return self._port_driver

    def has_driver(self):
        return self._port_driver is not None


class PortIn(PortWire):
    def __init__(self, parent, name, width=1):
        super().__init__(parent, name, width, output=False)

    def set_value(self, value):
        super().set_value(value)
        self.parent().update()


class PortOut(Port):
    def __init__(self, parent, name, width=1, delay_ns=1):
        super().__init__(parent, name, width, output=True)
        self._delay_ns = delay_ns  # Propagation delay for this port
        self._update_parent = False  # SHould this port update parent on change

    def update_parent(self, update_parent):
        self._update_parent = update_parent

    def set_delay_ns(self, delay_ns):
        self._delay_ns = delay_ns

    def set_value(self, value):
        self.parent().add_event(self, value, self._delay_ns)

    def delta_cycle(self, value):
        self.update_wires(value)
        if self._update_parent:
            self.parent().update()

    def set_driver(self, port):
        raise PortConnectionError(f"The port {self.path()}.{self.name()} cannot be driven")

    def get_driver(self):
        return None

    def has_driver(self):
        return False


class PortWireBit(PortWire):
    def __init__(self, parent, name, parent_port):
        super().__init__(parent, name, 1, False)
        self._parent_port = parent_port

    def set_value(self, value):
        super().set_value(value)
        self._parent_port.update()


class PortMultiBitWire(Port):
    def __init__(self, parent, name, width, output=False):
        super().__init__(parent, name, width, output)
        self._port_driver = None  # The port that drives this port
        self._bits = []
        for bit_id in range(self.width):
            self._bits.append(PortWireBit(parent, f"{self.name()}_{bit_id}", self))

    def set_value(self, value):
        if value == "X":
            return
        for bit_id, bit in enumerate(self._bits):
            bit_val = (value >> bit_id) & 1
            bit.value = bit_val

    def set_driver(self, port):
        self._port_driver = port

    def get_driver(self):
        return self._port_driver

    def has_driver(self):
        return self._port_driver is not None

    def get_bit(self, bit_id):
        return self._bits[bit_id]

    def update(self):
        for bit in self._bits:
            if bit.value == "X":
                self.update_wires("X")
                return
        value = 0
        for bit_id, bit in enumerate(self._bits):
            value = value | bit.value << bit_id
        self.update_wires(value)
