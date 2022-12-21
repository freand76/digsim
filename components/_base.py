import abc
import importlib
from enum import Enum, auto


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
    def __init__(self, parent, level=SignalLevel.UNKNOWN, propagation_delay_ns=0):
        self._name = None
        self._parent = parent
        self._level = level
        self._propagation_delay_ns = propagation_delay_ns
        self._wired_ports = []

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

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
    def wire(self):
        raise ConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        return self._wired_ports.append(port)

    @property
    def propagation_delay_ns(self):
        return self._propagation_delay_ns

    @property
    def wires(self):
        return self._wired_ports

    @abc.abstractmethod
    def set_level(self, level):
        pass

    @property
    @abc.abstractmethod
    def is_outport(self):
        pass

    @property
    def bitval(self):
        return SIGNAL_LEVEL_TO_STR[self._level]

    @property
    def intval(self):
        return 1 if self._level == SignalLevel.HIGH else 0

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


class InputPort(Port):
    def __init__(self, parent, update_parent=True):
        super().__init__(parent=parent)
        self._update_parent = update_parent

    @property
    def is_outport(self):
        return False

    def set_level(self, level):
        port_changed = self._level != level
        self._level = level
        if port_changed:
            self._parent.update()
            for port in self._wired_ports:
                port.level = level


class OutputPort(Port):
    def __init__(self, parent, propagation_delay_ns=10):
        super().__init__(
            parent=parent,
            level=SignalLevel.UNKNOWN,
            propagation_delay_ns=propagation_delay_ns,
        )
        self._next_level = SignalLevel.UNKNOWN

    @property
    def is_outport(self):
        return True

    def set_level(self, level):
        self._next_level = level
        self._parent.add_event(self)

    def delta_cycle(self):
        self._level = self._next_level
        for port in self._wired_ports:
            port.level = self.level


class Component(abc.ABC):
    def __init__(self, circuit, name=""):
        self._circuit = circuit
        self._name = name
        self._parent = None
        self._ports = []
        self._circuit.add_component(self)

    def init(self):
        pass

    def add_port(self, portname, port):
        self.__dict__[portname] = port
        port.name = portname
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

    def add_event(self, port):
        self.circuit.add_event(port)

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
