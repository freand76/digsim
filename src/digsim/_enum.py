# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from enum import Enum, auto


class PortDirection(Enum):
    IN = auto()
    OUT = auto()


class SignalLevel(Enum):
    UNKNOWN = auto()
    HIGH = auto()
    LOW = auto()
