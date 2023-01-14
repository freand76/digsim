# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import abc

from ._enum import PortDirection, SignalLevel


SIGNAL_LEVEL_TO_STR = {
    SignalLevel.UNKNOWN: "X",
    SignalLevel.HIGH: "1",
    SignalLevel.LOW: "0",
}


class WireConnectionError(Exception):
    """Exception for illegal connections"""


# pylint: disable=too-many-instance-attributes
class Port(abc.ABC):
    def __init__(self, parent, name, direction, default_level=SignalLevel.UNKNOWN):
        self._parent = parent
        self._direction = direction
        self._name = name
        self._driver_port = None
        self._wired_ports = []
        self._level = None
        self._width = 1
        self._default_level = default_level
        self.init()

    def init(self):
        self._level = self._default_level

    @property
    def name(self):
        return self._name

    @property
    def direction(self):
        return self._direction

    @property
    def parent(self):
        return self._parent

    @property
    def width(self):
        return self._width

    @property
    def path(self):
        return f"{self._parent.path}"

    @property
    def busbit(self):
        return False

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        self.set_level(level=level)

    @property
    def wire(self):
        raise WireConnectionError("Cannot get a wire")

    def has_driver(self):
        return self._driver_port is not None

    def set_driver(self, port):
        self._driver_port = port

    @property
    def driver(self):
        return self._driver_port

    @wire.setter
    def wire(self, port):
        if port.has_driver():
            raise WireConnectionError(f"The port {port.path}.{port.name} already has a driver")
        if self.width != port.width:
            raise WireConnectionError("Cannot connect ports with different widths")
        port.set_driver(self)
        self._wired_ports.append(port)
        if port.width == 1:
            port.level = self._level
        else:
            port.set_level(value=self.intval)

    def disconnect(self, port):
        index = self._wired_ports.index(port)
        del self._wired_ports[index]
        port.set_driver(None)

    @property
    def wires(self):
        return self._wired_ports

    @abc.abstractmethod
    def set_level(self, level=None, value=None):
        pass

    @property
    def bitval(self):
        return SIGNAL_LEVEL_TO_STR[self._level]

    @property
    def intval(self):
        return 1 if self._level == SignalLevel.HIGH else 0

    @property
    def vcdval(self):
        if self._level == SignalLevel.UNKNOWN:
            return "x"
        return self.intval

    def update_wires(self, level):
        self._level = level
        for port in self._wired_ports:
            port.level = self._level

    def __str__(self):
        return f"{self._parent.name}:{self.name}={SIGNAL_LEVEL_TO_STR[self._level]}"

    def to_dict_list(self):
        port_conn_list = []
        for port in self._wired_ports:
            port_conn_list.append(
                {
                    "src": f"{self.parent.name}.{self.name}",
                    "dst": f"{port.parent.name}.{port.name}",
                }
            )
        return port_conn_list


class ComponentPort(Port):
    def __init__(self, parent, name, direction, update_parent=True):
        super().__init__(parent=parent, name=name, direction=direction)
        self._update_parent = update_parent

    def set_level(self, level=None, value=None):
        port_changed = self.level != level
        if port_changed:
            self.update_wires(level)
        if port_changed and self._update_parent:
            self.parent.update()


class BusBit(Port):
    def __init__(self, parent, name, direction, bus_port):
        super().__init__(parent=parent, name=name, direction=direction)
        self._bus_port = bus_port

    @property
    def busbit(self):
        return True

    @property
    def bus_port(self):
        return self._bus_port

    def set_level(self, level=None, value=None):
        self._level = level
        self._bus_port.update()


class BusPort(Port):
    def __init__(self, parent, name, direction, width=1):
        super().__init__(parent=parent, name=name, direction=direction)
        self._width = width
        self._bus_value = -1
        self._bit_ports = []
        bit_direction = PortDirection.IN if direction == PortDirection.OUT else PortDirection.OUT
        for bit in range(width):
            self._bit_ports.append(BusBit(parent, f"name_b{bit}", bit_direction, self))

    def port_bit(self, bit):
        return self._bit_ports[bit]

    def set_level(self, level=None, value=None):
        self._bus_value = value

    @property
    def intval(self):
        return self._bus_value

    @property
    def vcdval(self):
        if self.intval == -1:
            return "x"
        return self.intval


class BusOutPort(BusPort):
    def __init__(self, parent, name, width=1):
        super().__init__(parent, name, PortDirection.OUT, width)
        self._bus_value = -1

    def connect_bit(self, bit, port):
        port.wire = self.port_bit(bit)

    def value(self):
        value = 0
        bit_val = 1
        for bit_port in self._bit_ports:
            if bit_port.level == SignalLevel.UNKNOWN:
                value = -1
                # break;
            elif bit_port.level == SignalLevel.HIGH:
                value = value | bit_val
            bit_val = bit_val << 1
        return value

    def update(self):
        value = self.value()
        super().set_level(value=value)
        for port in self._wired_ports:
            port.set_level(value=value)


class BusInPort(BusPort):
    def __init__(self, parent, name, width=1):
        super().__init__(parent, name, PortDirection.IN, width)
        self._bus_value = -1

    def connect_bit(self, bit, port):
        self.port_bit(bit).wire = port

    def set_level(self, level=None, value=None):
        if self._bus_value == value:
            return

        super().set_level(value=value)
        if value == -1:
            for bit_port in self._bit_ports:
                bit_port.level = SignalLevel.UNKNOWN
        else:
            for bit_port in self._bit_ports:
                old_level = bit_port.level
                if value & 1 == 1:
                    new_level = SignalLevel.HIGH
                else:
                    new_level = SignalLevel.LOW

                if old_level != new_level:
                    bit_port.level = new_level
                    bit_port.update_wires(new_level)

                value = value >> 1

    def update(self):
        self.parent.update()


class OutputPort(Port):
    def __init__(
        self,
        parent,
        name,
        update_parent_on_delta=False,
        default_level=SignalLevel.UNKNOWN,
    ):
        super().__init__(
            parent=parent,
            name=name,
            direction=PortDirection.OUT,
            default_level=default_level,
        )
        self._propagation_delay_ns = 10
        self._update_parent_on_delta = update_parent_on_delta

    def set_propagation_delay_ns(self, propagation_delay_ns):
        self._propagation_delay_ns = propagation_delay_ns

    def set_level(self, level=None, value=None):
        self.parent.add_event(self, level, self._propagation_delay_ns)

    def delta_cycle(self, level):
        self.update_wires(level)
        if self._update_parent_on_delta:
            self.parent.update()
