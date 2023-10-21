# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A wire placed in the GUI """

from digsim.circuit.components.atoms import PortConnectionError

from ._gui_object import GuiObject


class WireObject(GuiObject):
    """The class for wire placed in the GUI"""

    WIRE_CLICK_CLOSE_PIXELS = 10
    WIRE_TO_OBJECT_DIST = 5

    def __init__(self, app_model, port_a, port_b=None, connect=True):
        super().__init__()
        self._app_model = app_model
        self._src_port = None
        self._dst_port = None
        self._line_path = []
        if port_a is None:
            raise PortConnectionError("Cannot start a wire without a port")

        if port_b is not None:
            if port_a.is_output() and port_b.is_input():
                self._src_port = port_a
                self._dst_port = port_b
            elif port_a.is_input() and port_b.is_output():
                self._src_port = port_b
                self._dst_port = port_a
            else:
                raise PortConnectionError("Cannot connect to power of same type")
        else:
            if port_a.is_output():
                self._src_port = port_a
            else:
                self._dst_port = port_a

        if connect:
            self._connect()
                
    def _connect(self):
        if self._src_port is not None and self._dst_port is not None:
            self._src_port.wire = self._dst_port

    def disconnect(self):
        """Disconnect placed wire"""
        self._src_port.disconnect(self._dst_port)

    def set_end_port(self, port):
        """Set end port when creating a new wire"""
        if port.is_output() and self._src_port is None:
            self._src_port = port
        elif port.is_input() and self._dst_port is None:
            self._dst_port = port
        else:
            raise PortConnectionError("Cannot connect to power of same type")
        self._connect()

    def has_port(self, port):
        """Return True if port is alredy a part of this wire?"""
        return port in [self._src_port, self._dst_port]

    @property
    def key(self):
        """Get placed wire key, used by the model"""
        return (self._src_port, self._dst_port)

    @property
    def src_port(self):
        """Get the source port of the placed wire"""
        return self._src_port

    @property
    def dst_port(self):
        """Get the destination port of the placed wire"""
        return self._dst_port
