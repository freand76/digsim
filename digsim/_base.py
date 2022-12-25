import abc
import importlib
from enum import Enum, auto


class PortDirection(Enum):
    IN = auto()
    OUT = auto()


class SignalLevel(Enum):
    UNKNOWN = auto()
    HIGH = auto()
    LOW = auto()


SIGNAL_LEVEL_TO_STR = {
    SignalLevel.UNKNOWN: "X",
    SignalLevel.HIGH: "1",
    SignalLevel.LOW: "0",
}


class Port(abc.ABC):
    def __init__(self, parent, name, direction):
        self._parent = parent
        self._direction = direction
        self._name = name
        self._level = SignalLevel.UNKNOWN
        self._connected = False
        self._wired_ports = []

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
    def path(self):
        return f"{self._parent.path}"

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        self.set_level(level)

    @property
    def connected(self):
        return self._connected

    @connected.setter
    def connected(self, connect):
        if connect and self._connected:
            raise ConnectionError(
                f"The port {self.path}.{self.name} is alread connected"
            )
        self._connected = connect

    @property
    def wire(self):
        raise ConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        port.connected = True
        return self._wired_ports.append(port)

    @property
    def wires(self):
        return self._wired_ports

    @abc.abstractmethod
    def set_level(self, level):
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

    def set_level(self, level):
        port_changed = self.level != level
        if port_changed:
            self.update_wires(level)
        if port_changed and self._update_parent:
            self.parent.update()


class OutputPort(Port):
    def __init__(self, parent, name, propagation_delay_ns=10):
        super().__init__(
            parent=parent,
            name=name,
            direction=PortDirection.OUT,
        )
        self._propagation_delay_ns = propagation_delay_ns

    def set_propagation_delay_ns(self, propagation_delay_ns):
        self._propagation_delay_ns = propagation_delay_ns

    def set_level(self, level):
        self._parent.add_event(self, level, self._propagation_delay_ns)

    def delta_cycle(self, level):
        self.update_wires(level)


class Component(abc.ABC):
    def __init__(self, circuit, name=""):
        self._circuit = circuit
        self._name = name
        self._parent = None
        self._ports = []
        self._circuit.add_component(self)

    def init(self):
        pass

    def add_port(self, port):
        self.__dict__[port.name] = port
        self._ports.append(port)

    @property
    def path(self):
        if self._parent is not None:
            return f"{self._parent.path}.{self.name}"
        return f"{self.name}"

    @property
    def ports(self):
        return self._ports

    def port(self, portname):
        for port in self._ports:
            if port.name == portname:
                return port
        raise ValueError("Port not found")

    @property
    def circuit(self):
        return self._circuit

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    def update(self):
        pass

    def add_event(self, port, level, propagation_delay_ns):
        self.circuit.add_event(port, level, propagation_delay_ns)

    def __str__(self):
        comp_str = f"{self.name}\n"
        for port in self.ports:
            comp_str += f"-{port.name}={port.bitval}\n"
        return comp_str

    @classmethod
    def from_dict(cls, circuit, json_component):
        component_name = json_component["name"]
        component_type = json_component["type"]

        py_module_name = ".".join(component_type.split(".")[0:-1])
        py_class_name = component_type.split(".")[-1]

        module = importlib.import_module(py_module_name)
        class_ = getattr(module, py_class_name)
        return class_(circuit=circuit, name=component_name)

    def to_dict(self):
        return {
            "name": self.name,
            "type": f"{type(self).__module__}.{type(self).__name__}",
        }


class MultiComponent(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self._components = []

    def add(self, component):
        self._components.append(component)
        component.parent = self
