# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A Dip-switch component """

from .atoms import CallbackComponent, PortOutDelta


class DipSwitch(CallbackComponent):
    """On/Off Switch  component class"""

    NOF_BITS = 8

    def __init__(self, circuit, name=None, bus=False):
        super().__init__(circuit, name)
        self._bus = bus
        self.parameter_set("bus", bus)
        self._select = None
        if self._bus:
            portout = PortOutDelta(self, "O", delay_ns=0, width=self.NOF_BITS)
            self.add_port(portout)
        else:
            for index in range(0, self.NOF_BITS):
                portout = PortOutDelta(self, f"{index}", delay_ns=0)
                self.add_port(portout)

    def bits(self):
        """Get number of bits in dipswitch"""
        return self.NOF_BITS

    def is_set(self, bit):
        """Test if dip switch bit is set"""
        if self._bus:
            value = self.port("O").value
            return (value & 1 << bit) != 0
        return self.port(f"{bit}").value == 1

    def default_state(self):
        for port in self.outports():
            port.value = 0

    def select(self, idx):
        """Select bit in dipswitch (for toggle)"""
        self._select = idx

    def _toggle_bit(self, bit):
        port = self.port(f"{bit}")
        if port.value == 1:
            port.value = 0
        else:
            port.value = 1

    def _toggle_bus(self, bit):
        value = self.port("O").value
        value = value ^ 1 << bit
        self.port("O").value = value

    def toggle(self):
        """Toggle the switch"""
        if self._select is None:
            return
        if self._bus:
            self._toggle_bus(self._select)
        else:
            self._toggle_bit(self._select)

    def onpress(self):
        self.toggle()

    @property
    def has_action(self):
        return True

    @classmethod
    def get_parameters(cls):
        return {
            "bus": {
                "type": bool,
                "default": False,
                "description": "Bus output",
                "reconfigurable": False,
            },
        }
