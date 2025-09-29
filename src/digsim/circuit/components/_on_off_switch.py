# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""An On/Off Switch  component"""

import logging

from .atoms import CallbackComponent, PortOutDelta


class OnOffSwitch(CallbackComponent):
    """On/Off Switch  component class"""

    def __init__(self, circuit, name=None, start_on=False):
        super().__init__(circuit, name)
        portout = PortOutDelta(self, "O", delay_ns=0)
        self.add_port(portout)
        portout.update_parent(True)
        self._on = False
        if start_on:
            logging.warning("Setting 'start_on' has been removed")

    def _set(self, state):
        self._on = state
        self.O.value = 1 if state else 0

    def default_state(self):
        self._set(False)

        self.turn_off()

    def turn_on(self):
        """Turn on the switch"""
        self.O.value = 1
        self._on = True

    def turn_off(self):
        """Turn off the switch"""
        self._set(False)

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
        return self._on
