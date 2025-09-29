# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the LED component"""

from .atoms import CallbackComponent, PortIn


class Led(CallbackComponent):
    """LED component class"""

    def __init__(self, circuit, name=None, callback=None):
        super().__init__(circuit, name, callback)
        self.add_port(PortIn(self, "I"))

    @property
    def active(self):
        return self.I.has_driver() and self.I.value == 1
