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
    def __init__(self, parent, level=SignalLevel.UNKNOWN):
        self._parent = parent
        self._level = level
        self._name = None
        self._destinations = []

    @property
    def level(self):
        return self._level

    @property
    def parent(self):
        return self._parent

    @property
    def name(self):
        return self._name

    @property
    def destinations(self):
        return self._destinations

    @property
    def path(self):
        return f"{self.parent.path}"

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def parent_port(self):
        return self._parent.portname_from_instance(self)

    @abc.abstractmethod
    def set_level(self, level):
        pass

    @level.setter
    def level(self, level):
        self.set_level(level)

    @property
    @abc.abstractmethod
    def iotype(self):
        pass

    @property
    def val(self):
        return SIGNAL_LEVEL_TO_STR[self._level]

    @property
    def intval(self):
        return 1 if self.level == SignalLevel.HIGH else 0

    def __str__(self):
        return f"{self.parent.name}:{self.name}={SIGNAL_LEVEL_TO_STR[self._level]}"


class InputPort(Port):
    def __init__(self, parent, update_parent=True):
        super().__init__(parent=parent)
        self._update_parent = update_parent

    @property
    def iotype(self):
        return "IN"

    def set_level(self, level):
        port_changed = self._level != level
        self._level = level
        if port_changed:
            self.parent.update()


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
    def __init__(self, parent):
        super().__init__(parent=parent, level=SignalLevel.UNKNOWN)
        self._next_level = SignalLevel.UNKNOWN

    def connect(self, dest):
        self._destinations.append(dest)

    @property
    def iotype(self):
        return "OUT"

    @property
    def next(self):
        return SIGNAL_LEVEL_TO_STR[self._next_level]

    def set_level(self, level):
        self._next_level = level
        if self._next_level != self._level:
            self.parent.delta_cycle_needed(self)

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
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    @property
    def path(self):
        if self.parent is not None:
            return f"{self.parent.path}.{self.name}"
        else:
            return f"{self.name}"

    @property
    def inports(self):
        ports = []
        for port in self._ports:
            if isinstance(port, InputPort):
                ports.append(port)
        return ports

    @property
    def outports(self):
        ports = []
        for port in self._ports:
            if isinstance(port, OutputPort):
                ports.append(port)
        return ports

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

    def delta_cycle_needed(self, port):
        self.circuit.delta_cycle_needed(port)

    def __str__(self):
        comp_str = f"{self.name}"
        for port in self.inports:
            comp_str += f" {port.name}={port.val}"
        comp_str += " =>"
        for port in self.outports:
            comp_str += f" {port.name}={port.val}>{port.next}"
        return comp_str


class ActorComponent(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)

    def actor_event(self):
        self.circuit.delta_cycle()


class MultiComponent(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self._components = []

    def add(self, component):
        self._components.append(component)
        component.parent = self
