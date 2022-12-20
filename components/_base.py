import abc
import importlib
from enum import Enum, auto


class ConnectionError(Exception):
    pass


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
        self._destinations = []

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

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
    def propagation_delay_ns(self):
        return self._propagation_delay_ns

    @property
    def destinations(self):
        return self._destinations

    @abc.abstractmethod
    def set_level(self, level):
        pass

    @property
    @abc.abstractmethod
    def iotype(self):
        pass

    @property
    def bitval(self):
        return SIGNAL_LEVEL_TO_STR[self._level]

    @property
    def intval(self):
        return 1 if self._level == SignalLevel.HIGH else 0

    def __str__(self):
        return f"{self._parent.name}:{self.name}={SIGNAL_LEVEL_TO_STR[self._level]}"


class InputPort(Port):
    def __init__(self, parent, update_parent=True):
        super().__init__(parent=parent)
        self._update_parent = update_parent

    @property
    def iotype(self):
        return "IN"

    def connect(self, dest):
        raise ConnectionError("Cannot make connection from InputPort")

    def set_level(self, level):
        port_changed = self._level != level
        self._level = level
        if port_changed:
            self._parent.update()


class InputFanOutPort(InputPort):
    def __init__(self, parent):
        super().__init__(parent=parent)

    def connect(self, dest):
        self._destinations.append(dest)

    def set_level(self, level):
        if self._level != level:
            self._level = level
            for dest in self.destinations:
                dest.level = level


class OutputPort(Port):
    def __init__(self, parent, propagation_delay_ns=10):
        super().__init__(
            parent=parent,
            level=SignalLevel.UNKNOWN,
            propagation_delay_ns=propagation_delay_ns,
        )
        self._next_level = SignalLevel.UNKNOWN

    def connect(self, dest):
        self._destinations.append(dest)

    @property
    def iotype(self):
        return "OUT"

    def set_level(self, level):
        self._next_level = level
        if self._next_level != self._level:
            self._parent.add_event(self)

    def delta_cycle(self):
        if self._next_level != self._level:
            self._level = self._next_level
            for dest in self.destinations:
                dest.level = self.level


class Component(abc.ABC):
    @classmethod
    def from_json(cls, circuit, json_component):
        component_name = json_component["name"]
        component_type = json_component["type"]

        py_module_name = ".".join(component_type.split(".")[0:-1])
        py_class_name = component_type.split(".")[-1]

        module = importlib.import_module(py_module_name)
        class_ = getattr(module, py_class_name)
        return class_(circuit=circuit, name=component_name)

    def __init__(self, circuit, name=""):
        self._circuit = circuit
        self._name = name
        self._parent = None
        self._ports = []
        self._circuit.add_component(self)

    def init(self):
        pass

    def add_port(self, portname, port):
        port.name = portname
        self._ports.append(port)

    @property
    def path(self):
        if self._parent is not None:
            return f"{self._parent.path}.{self.name}"
        else:
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

    def update(self):
        pass

    def add_event(self, port):
        self.circuit.add_event(port)

    def __str__(self):
        comp_str = f"{self.name}\n"
        for port in self.ports:
            comp_str += f"-{port.name}={port.bitval}\n"
        return comp_str


class MultiComponent(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self._components = []

    def add(self, component):
        self._components.append(component)
        component._parent = self
