# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A PushButton component"""

from .atoms import CallbackComponent, PortOutImmediate


class PushButton(CallbackComponent):
    """PushButton component class"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        portout = PortOutImmediate(self, "O")
        self.add_port(portout)
        portout.update_parent(True)

    def default_state(self):
        self.release()

    def push(self):
        """Push pushbutton"""
        self.O.value = 1

    def release(self):
        """Release pushbutton"""
        self.O.value = 0

    def reconfigure(self):
        self.release()

    @property
    def has_action(self):
        return True

    @property
    def active(self):
        return self.O.value == 1

    def onpress(self):
        self.push()

    def onrelease(self):
        self.release()
