from enum import Enum, auto


class PortDirection(Enum):
    IN = auto()
    OUT = auto()


class SignalLevel(Enum):
    UNKNOWN = auto()
    HIGH = auto()
    LOW = auto()
