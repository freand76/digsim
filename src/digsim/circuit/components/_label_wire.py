# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Label Wire components module"""

from .atoms import Component, DigsimException, PortIn, PortWire


class _LabelWireStorage:
    """Singleton class with label wires"""

    _instance = None
    _wire_drivers: dict[str, PortWire] = {}
    _wire_sinks: dict[str, PortIn] = {}

    def __new__(cls):
        if cls._instance is None:
            if not cls._instance:
                cls._instance = super(_LabelWireStorage, cls).__new__(cls)
        return cls._instance

    def clear(self):
        """Remove all wires"""
        self._wire_drivers = {}
        self._wire_sinks = {}

    def get_labels(self):
        """Get label list"""
        return list(self._wire_drivers.keys())

    def get_wire_width(self, label):
        """Get width of wire"""
        driver_port = self._wire_drivers.get(label)
        if driver_port is None:
            return None
        return driver_port.width

    def add_driver(self, label, driver_port):
        """Add driver port with label"""
        if label in self._wire_drivers:
            raise DigsimException(f"Wire Driver '{label}' already added")
        self._wire_drivers[label] = driver_port

    def _get_driver(self, label):
        driver_port = self._wire_drivers.get(label)
        if driver_port is None:
            raise DigsimException(f"Wire Driver '{label}' not found")
        return driver_port

    def remove_driver(self, label):
        """Remove driver"""
        driver_port = self._get_driver(label)
        for sink_port, sink_label in self._wire_sinks.items():
            if label == sink_label:
                driver_port.disconnect(sink_port)
        del self._wire_drivers[label]

    def add_sink(self, label, sink_port):
        """Add driver port with label"""
        if sink_port in self._wire_sinks:
            raise DigsimException(f"Wire Sink '{label}' already added")
        self._wire_sinks[sink_port] = label

    def remove_sink(self, sink_port):
        """Remove sink"""
        del self._wire_sinks[sink_port]

    def connect(self, sink_port):
        """Connect sink port if needed"""
        if not sink_port.has_driver():
            label = self._wire_sinks.get(sink_port)
            if label is None:
                raise DigsimException("Wire Sink not found")
            driver_port = self._get_driver(label)
            driver_port.wire = sink_port


class LabelWireIn(Component):
    """LabelWireIn component class"""

    def __init__(self, circuit, name=None, label=None, width=1):
        super().__init__(circuit, name)
        self._label = label
        self._port_in = PortWire(self, self._label, width=width)
        self.add_port(self._port_in)
        self.parameter_set("label", self._label)
        self.parameter_set("width", width)
        self._label_wires = _LabelWireStorage()
        self._label_wires.add_driver(self._label, self._port_in)

    def clear(self):
        self._label_wires.clear()

    def label(self):
        """Return Label"""
        return self._label

    def remove_connections(self):
        self._label_wires.remove_driver(self._label)
        super().remove_connections()

    @classmethod
    def get_parameters(cls):
        label_wires = _LabelWireStorage()
        label_list = label_wires.get_labels()

        return {
            "label": {
                "type": "str",
                "single_line": True,
                "default": "WireLabel",
                "description": "Label name",
                "invalid_list": label_list,
            },
            "width": {
                "type": "int",
                "min": 1,
                "max": 32,
                "default": 1,
                "description": "Bitwidth of wire",
            },
        }


class LabelWireOut(Component):
    """LabelWireOut component class"""

    def __init__(self, circuit, name=None, label=None, width=1):
        super().__init__(circuit, name)
        self._label_wires = _LabelWireStorage()
        label_width = self._label_wires.get_wire_width(label)
        width = label_width if label_width is not None else width
        self._label = label
        self._port_out = PortWire(self, self._label, width=width, output=True)
        self.add_port(self._port_out)
        self.parameter_set("label", self._label)
        self.parameter_set("width", width)
        self._label_wires = _LabelWireStorage()
        self._label_wires.add_sink(self._label, self._port_out)

    def clear(self):
        self._label_wires.clear()

    def label(self):
        """Return Label"""
        return self._label

    def init(self):
        self._label_wires.connect(self._port_out)
        super().init()

    def remove_connections(self):
        self._label_wires.remove_sink(self._port_out)
        super().remove_connections()

    @classmethod
    def get_parameters(cls):
        label_wires = _LabelWireStorage()
        label_list = label_wires.get_labels()

        return {
            "label": {
                "type": "list",
                "items": label_list,
                "description": "Select label",
            }
        }
