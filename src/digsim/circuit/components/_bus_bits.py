# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Module with the bus/bit <=> bus/bit components"""

from .atoms import Component, PortMultiBitWire


class Bus2Bits(Component):
    """Bus to Bits splitter"""

    def __init__(self, circuit, name="Bus2Bits", width=1):
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width)
        self.add_port(self._bus)
        for bit_id in range(width):
            bit_port = self._bus.get_bit(bit_id)
            self.add_port(bit_port)

    @classmethod
    def get_parameters(cls):
        return {
            "width": {
                "type": int,
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
        }

    def settings_to_dict(self):
        return {"width": self.bus.width}


class Bits2Bus(Component):
    """Bits to Bus merger"""

    def __init__(self, circuit, name="Bits2Bus", width=1):
        super().__init__(circuit, name)
        self._bus = PortMultiBitWire(self, "bus", width=width, output=True)
        self.add_port(self._bus)
        for bit_id in range(width):
            bit_port = self._bus.get_bit(bit_id)
            self.add_port(bit_port)

    @classmethod
    def get_parameters(cls):
        return {
            "width": {
                "type": int,
                "min": 2,
                "max": 32,
                "default": 2,
                "description": "Bus width",
            },
        }

    def settings_to_dict(self):
        return {"width": self.bus.width}