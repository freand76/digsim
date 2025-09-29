# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Static Leve component"""

from .atoms import Component, PortOutImmediate


class StaticValue(Component):
    """Static value component class"""

    def __init__(self, circuit, name=None, width=1, value=0):
        super().__init__(circuit, name)
        self.parameter_set("width", width)
        self.parameter_set("value", value)
        self.add_port(PortOutImmediate(self, "O", width=width))

    def default_state(self):
        self.O.value = self.parameter_get("value")

    def reconfigure(self):
        self.O.value = self.parameter_get("value")

    @property
    def active(self):
        return self.parameter_get("width") == 1 and self.parameter_get("value") == 1

    @classmethod
    def get_parameters(cls):
        return {
            "value": {
                "type": "width_pow2",
                "default": 0,
                "description": "Static value",
                "reconfigurable": True,
            },
            "width": {
                "type": "int",
                "min": 1,
                "max": 16,
                "default": 1,
                "description": "Static value bitwidth",
            },
        }
