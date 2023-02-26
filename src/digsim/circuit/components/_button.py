# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A PushButton component """

from .atoms import CallbackComponent, PortDriver


class PushButton(CallbackComponent):
    """PushButton component class"""

    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        portout = PortDriver(self, "O")
        self.add_port(portout)
        portout.update_parent(True)
        self.parameter_set("inverted", inverted)

    def default_state(self):
        self.release()

    def push(self):
        """Push pushbutton"""
        if self.parameter_get("inverted"):
            self.O.value = 0
        else:
            self.O.value = 1

    def release(self):
        """Release pushbutton"""
        if self.parameter_get("inverted"):
            self.O.value = 1
        else:
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

    @classmethod
    def get_parameters(cls):
        return {
            "inverted": {
                "type": bool,
                "default": False,
                "description": "Button output is inverted",
                "reconfigurable": True,
            },
        }
