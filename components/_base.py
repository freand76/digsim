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

    @property
    def level(self):
        return self._level

    @property
    def parent_port(self):
        return self._parent.portname_from_instance(self)

    @level.setter
    def level(self, level):
        port_changed = level != self._level
        self._level = level
        self.update(port_changed)

    @property
    @abc.abstractmethod
    def iotype(self):
        pass

    @abc.abstractmethod
    def update(self, port_changed=False):
        pass

    def __str__(self):
        return SIGNAL_LEVEL_TO_STR[self._level]


class InputPort(Port):
    def __init__(self, parent, update_parent=True):
        super().__init__(parent=parent)
        self._update_parent = update_parent

    @property
    def iotype(self):
        return "IN"

    def update(self, port_changed=False):
        if port_changed and self._update_parent:
            self._parent.update()


class InputFanOutPort(InputPort):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self._destinations = []

    def connect(self, dest):
        self._destinations.append(dest)

    def update(self, port_changed=False):
        for dest in self._destinations:
            dest.level = self.level


class OutputPort(Port):
    def __init__(self, parent):
        super().__init__(parent=parent, level=SignalLevel.UNKNOWN)
        self._destinations = []

    def connect(self, dest):
        self._destinations.append(dest)

    @property
    def iotype(self):
        return "OUT"

    def update(self, port_changed=False):
        if port_changed:
            for dest in self._destinations:
                dest.level = self.level


class Component(abc.ABC):
    @classmethod
    def from_json(cls, json_component):
        component_name = json_component["name"]
        component_type = json_component["type"]

        py_module_name = ".".join(component_type.split(".")[0:-1])
        py_class_name = component_type.split(".")[-1]

        module = importlib.import_module(py_module_name)
        class_ = getattr(module, py_class_name)
        return class_(name=component_name)

    def __init__(self, name):
        self._name = name
        self._input_ports = {}
        self._output_ports = {}

    def init(self):
        pass

    def add_port(self, portname, port):
        if isinstance(port, InputPort):
            self._input_ports[portname] = port
        elif isinstance(port, OutputPort):
            self._output_ports[portname] = port

    @property
    def inports(self):
        return [key for key in self._input_ports.keys()]

    @property
    def outports(self):
        return [key for key in self._output_ports.keys()]

    def portname_from_instance(self, port):
        ports = self._input_ports if isinstance(port, InputPort) else self._output_ports
        for portname, port_instance in ports.items():
            if port == port_instance:
                return portname

    def inport(self, portname):
        return self._input_ports[portname]

    def outport(self, portname):
        return self._output_ports[portname]

    def port(self, portname):
        if portname in self._input_ports:
            return self.inport(portname)
        else:
            return self.outport(portname)

    @property
    def name(self):
        return self._name

    def update(self):
        pass

    def delta(self):
        pass
