import abc
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
        self._level = level
        self._parent = parent

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        port_changed = level != self._level
        self._level = level
        self.update(port_changed)

    @abc.abstractmethod
    def type(self):
        pass

    @abc.abstractmethod
    def update(self, port_changed=False):
        pass

    def __str__(self):
        return SIGNAL_LEVEL_TO_STR[self._level]


class InputPort(Port):
    def __init__(self, parent):
        super().__init__(parent=parent)

    def type(self):
        return "IN"

    def update(self, port_changed=False):
        if port_changed:
            self._parent.update()


class OutputPort(Port):
    def __init__(self, parent):
        super().__init__(parent=parent, level=SignalLevel.LOW)
        self._destinations = []

    def connect(self, dest):
        self._destinations.append(dest)

    def type(self):
        return "OUT"

    def update(self, port_changed=False):
        for dest in self._destinations:
            dest.level = self.level


class Component(abc.ABC):
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

    def inport(self, portname):
        return self._input_ports[portname]

    def outport(self, portname):
        return self._output_ports[portname]

    @property
    def name(self):
        return self._name

    def update(self):
        pass
