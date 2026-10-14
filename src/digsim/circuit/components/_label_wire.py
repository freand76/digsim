# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Label Wire components module"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .atoms import Component, DigsimException, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class _LabelWireStorage:
    """Singleton class with label wires"""

    _instance: _LabelWireStorage | None = None
    _wire_drivers: dict[str, PortWire]
    _wire_sinks: dict[PortWire, str]

    def __new__(cls) -> _LabelWireStorage:  # noqa: PYI034 (singleton)
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.clear()
        return cls._instance

    def clear(self) -> None:
        """Remove all wires"""
        self._wire_drivers = {}
        self._wire_sinks = {}

    def get_labels(self) -> list[str]:
        """Get label list"""
        return list(self._wire_drivers.keys())

    def get_wire_width(self, label: str) -> int | None:
        """Get width of wire"""
        driver_port = self._wire_drivers.get(label)
        if driver_port is None:
            return None
        return driver_port.width

    def check_new_driver(self, label: str) -> None:
        """Raise an exception if label already has a driver"""
        if label in self._wire_drivers:
            raise DigsimException(f"Wire Driver '{label}' already added")

    def add_driver(self, label: str, driver_port: PortWire) -> None:
        """Add driver port with label"""
        self.check_new_driver(label)
        self._wire_drivers[label] = driver_port

    def _get_driver(self, label: str) -> PortWire:
        driver_port = self._wire_drivers.get(label)
        if driver_port is None:
            raise DigsimException(f"Wire Driver '{label}' not found")
        return driver_port

    def remove_driver(self, label: str) -> None:
        """Remove driver"""
        driver_port = self._get_driver(label)
        for sink_port, sink_label in self._wire_sinks.items():
            if label == sink_label:
                driver_port.disconnect(sink_port)
        del self._wire_drivers[label]

    def add_sink(self, label: str, sink_port: PortWire) -> None:
        """Add driver port with label"""
        if sink_port in self._wire_sinks:
            raise DigsimException(f"Wire Sink '{label}' already added")
        self._wire_sinks[sink_port] = label

    def remove_sink(self, sink_port: PortWire) -> None:
        """Remove sink"""
        del self._wire_sinks[sink_port]

    def connect(self, sink_port: PortWire) -> None:
        """Connect sink port if needed"""
        if not sink_port.has_driver():
            label = self._wire_sinks.get(sink_port)
            if label is None:
                raise DigsimException("Wire Sink not found")
            driver_port = self._get_driver(label)
            driver_port.wire = sink_port


class LabelWireIn(Component):
    """LabelWireIn component class"""

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "", width: int = 1
    ) -> None:
        self._label_wires = _LabelWireStorage()
        # Check before the component is added to the circuit
        self._label_wires.check_new_driver(label)
        super().__init__(circuit, name)
        self._label = label
        self._port_in = PortWire(self, self._label, width=width)
        self.add_port(self._port_in)
        self.parameter_set("label", self._label)
        self.parameter_set("width", width)
        self._label_wires.add_driver(self._label, self._port_in)

    def clear(self) -> None:
        self._label_wires.clear()

    def label(self) -> str:
        """Return Label"""
        return self._label

    def remove_connections(self) -> None:
        self._label_wires.remove_driver(self._label)
        super().remove_connections()

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
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

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "", width: int = 1
    ) -> None:
        super().__init__(circuit, name)
        self._label_wires = _LabelWireStorage()
        label_width = self._label_wires.get_wire_width(label)
        width = label_width if label_width is not None else width
        self._label = label
        self._port_out = PortWire(self, self._label, width=width, output=True)
        self.add_port(self._port_out)
        self.parameter_set("label", self._label)
        self.parameter_set("width", width)
        self._label_wires.add_sink(self._label, self._port_out)

    def clear(self) -> None:
        self._label_wires.clear()

    def label(self) -> str:
        """Return Label"""
        return self._label

    def init(self) -> None:
        self._label_wires.connect(self._port_out)
        super().init()

    def remove_connections(self) -> None:
        self._label_wires.remove_sink(self._port_out)
        super().remove_connections()

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        label_wires = _LabelWireStorage()
        label_list = label_wires.get_labels()

        return {
            "label": {
                "type": "list",
                "items": label_list,
                "description": "Select label",
            }
        }
