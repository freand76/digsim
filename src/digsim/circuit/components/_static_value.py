# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Module with the Static Leve component """

from .atoms import Component, PortOut


class StaticValue(Component):
    """Static value component class"""

    def __init__(self, circuit, name="StaticValue", width=1, value=0):
        super().__init__(circuit, name)
        self._width = width
        self._value = value
        self.add_port(PortOut(self, "O", width=width, delay_ns=0))

    def init(self):
        super().init()
        self.O.value = self._value

    @property
    def active(self):
        return self._width == 1 and self._value == 1

    @classmethod
    def get_parameters(cls):
        return {
            "value": {
                "type": int,
                "min": 0,
                "max": "width_dependent",
                "default": 0,
                "description": "Static value",
            },
            "width": {
                "type": int,
                "min": 1,
                "max": 16,
                "default": 1,
                "description": "Static value bitwidth",
            },
        }

    def settings_to_dict(self):
        return {"value": self._value, "width": self._width}
