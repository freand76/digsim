# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import CallbackComponent, ComponentPort, PortDirection, SignalLevel


class Led(CallbackComponent):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name, callback)
        self.add_port(ComponentPort(self, "I", PortDirection.IN))

    @property
    def active(self):
        return self.I.has_driver() and self.I.level == SignalLevel.HIGH
