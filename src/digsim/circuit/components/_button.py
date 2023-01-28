# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A PushButton component """

from .atoms import CallbackComponent, PortOut


class PushButton(CallbackComponent):
    """PushButton component class"""

    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        self._inverted = inverted
        portout = PortOut(self, "O", delay_ns=0)
        self.add_port(portout)
        portout.update_parent(True)

    def init(self):
        super().init()
        self.release()

    def push(self):
        if self._inverted:
            self.O.value = 0
        else:
            self.O.value = 1

    def release(self):
        if self._inverted:
            self.O.value = 1
        else:
            self.O.value = 0

    @property
    def has_action(self):
        return True

    @property
    def active(self):
        if self._inverted:
            return self.O.value == 0
        return self.O.value == 1

    def onpress(self):
        self.push()

    def onrelease(self):
        self.release()
