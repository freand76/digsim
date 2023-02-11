# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" Module with the Static Logic components """

from .atoms import Component, PortOut


class VDD(Component):
    """VDD / Logic1 component class"""

    def __init__(self, circuit, name="VDD"):
        super().__init__(circuit, name)
        self.add_port(PortOut(self, "O", delay_ns=0))

    def init(self):
        super().init()
        self.O.value = 1


class GND(Component):
    """GND / Logic0 component class"""

    def __init__(self, circuit, name="GND"):
        super().__init__(circuit, name)
        self.add_port(PortOut(self, "O", delay_ns=0))

    def init(self):
        super().init()
        self.O.value = 0


class StaticLevel(Component):
    """Static level component class"""

    def __init__(self, circuit, name="StaticLevel", output=False):
        super().__init__(circuit, name)
        self._output = output
        self.add_port(PortOut(self, "O", delay_ns=0))

    def init(self):
        super().init()
        if self._output:
            self.O.value = 1
        else:
            self.O.value = 0

    @property
    def active(self):
        return self._output

    @classmethod
    def get_parameters(cls):
        return {
            "output": {
                "type": bool,
                "default": False,
                "description": "Output level is High",
            },
        }

    def settings_to_dict(self):
        return {"output": self._output}
