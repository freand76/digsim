# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the bus/bit <=> bus/bit components"""

from .atoms import Component, PortMultiBitWire


class Bus2Wires(Component):
    """Bus to Bits splitter"""

    def __init__(self, circuit, name=None, width=1, enable=None):
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width)
        self.add_port(self._bus)
        self._enable = enable
        if self._enable is None:
            self._enable = list(range(width))

        for bit_id in range(width):
            if bit_id in self._enable:
                bit_port = self._bus.get_bit(bit_id)
                self.add_port(bit_port)

        self.parameter_set("width", width)
        self.parameter_set("enable", enable)

    @classmethod
    def get_parameters(cls):
        return {
            "width": {
                "type": "int",
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
            "enable": {
                "type": "width_bool",
                "default": None,
                "description": "Enable bit",
            },
        }


class Wires2Bus(Component):
    """Bits to Bus merger"""

    def __init__(self, circuit, name=None, width=1):
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width, output=True)
        self.add_port(self._bus)
        for bit_id in range(width):
            bit_port = self._bus.get_bit(bit_id)
            self.add_port(bit_port)
        self.parameter_set("width", width)

    @classmethod
    def get_parameters(cls):
        return {
            "width": {
                "type": "int",
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
        }
