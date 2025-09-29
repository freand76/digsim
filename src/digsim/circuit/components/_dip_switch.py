# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A Dip-switch component"""

from .atoms import CallbackComponent, PortOutImmediate


class DipSwitch(CallbackComponent):
    """On/Off Switch  component class"""

    def __init__(self, circuit, name=None, bits=8):
        super().__init__(circuit, name)
        self._bits = bits
        self.parameter_set("bits", bits)
        self._select = None
        for index in range(0, self._bits):
            portout = PortOutImmediate(self, f"{index}")
            self.add_port(portout)

    def bits(self):
        """Get number of bits in dipswitch"""
        return self._bits

    def is_set(self, bit):
        """Test if dip switch bit is set"""
        return self.port(f"{bit}").value == 1

    def default_state(self):
        for port in self.outports():
            port.value = 0

    def select(self, idx):
        """Select bit in dipswitch (for toggle)"""
        self._select = idx

    def selected(self):
        """Get selected bit in dipswitch (for gui)"""
        return self._select

    def _toggle_bit(self, bit):
        if bit >= self._bits:
            return
        port = self.port(f"{bit}")
        if port.value == 1:
            port.value = 0
        else:
            port.value = 1

    def toggle(self):
        """Toggle the switch"""
        if self._select is None:
            return
        self._toggle_bit(self._select)

    def onpress(self):
        self.toggle()

    @property
    def has_action(self):
        return True

    @classmethod
    def get_parameters(cls):
        return {
            "bits": {
                "type": "int",
                "min": 2,
                "max": 8,
                "default": 8,
                "description": "Number of bits",
            },
        }
