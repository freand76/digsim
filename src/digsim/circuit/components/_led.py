# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import CallbackComponent, PortIn


class Led(CallbackComponent):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name, callback)
        self.add_port(PortIn(self, "I"))

    @property
    def active(self):
        return self.I.has_driver() and self.I.value == 1
