# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" An On/Off Switch  component """

from .atoms import CallbackComponent, PortOut


class OnOffSwitch(CallbackComponent):
    """On/Off Switch  component class"""

    def __init__(self, circuit, name="OnOffSwitch", start_on=False):
        super().__init__(circuit, name)
        portout = PortOut(self, "O", delay_ns=0)
        self.add_port(portout)
        portout.update_parent(True)
        self._on = False
        self._start_on = start_on

    def _set(self, set_on):
        if set_on:
            self.turn_on()
        else:
            self.turn_off()

    def init(self):
        super().init()
        self._set(self._start_on)

    def turn_on(self):
        """Turn on the switch"""
        self.O.value = 1
        self._on = True

    def turn_off(self):
        """Turn off the switch"""
        self.O.value = 0
        self._on = False

    def toggle(self):
        """Toggle the switch"""
        self._set(not self._on)

    def onpress(self):
        self.toggle()

    @property
    def has_action(self):
        return True

    @property
    def active(self):
        return self.O.value == 1
