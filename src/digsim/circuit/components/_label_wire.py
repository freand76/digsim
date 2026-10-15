# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Label Wire components module"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from .atoms import Component, DigsimException, PortWire


if TYPE_CHECKING:
    from digsim.circuit import Circuit


def _drivers(circuit: Circuit) -> dict[str, LabelWireIn]:
    """The label wire drivers in the circuit, by label"""
    return {comp.label(): comp for comp in circuit.components if isinstance(comp, LabelWireIn)}


def _sinks(circuit: Circuit, label: str) -> list[LabelWireOut]:
    """The label wire sinks in the circuit with the label"""
    return [
        comp
        for comp in circuit.components
        if isinstance(comp, LabelWireOut) and comp.label() == label
    ]


class LabelWireIn(Component):
    """
    A Wire Sink: passes its input to every LabelWireOut with the same label, without a drawn wire.

    Ports:
        <label>: Input, named like the label, `width` bits.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        label: The label.
        width: The number of bits.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "", width: int = 1
    ) -> None:
        # Check before the component is added to the circuit
        if label in _drivers(circuit):
            raise DigsimException(f"Wire Driver '{label}' already added")
        super().__init__(circuit, name)
        self._label = label
        self._port_in = PortWire(self, self._label, width=width)
        self.add_port(self._port_in)
        self.parameter_set("label", self._label)
        self.parameter_set("width", width)

    def label(self) -> str:
        """Return Label"""
        return self._label

    @property
    def port_in(self) -> PortWire:
        """The port that drives the sinks"""
        return self._port_in

    def remove_connections(self) -> None:
        for sink in _sinks(self.circuit, self._label):
            self._port_in.disconnect(sink.port_out)
        super().remove_connections()

    @classmethod
    def _label_parameters(cls, label_list: list[str]) -> dict[str, dict[str, Any]]:
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

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return cls._label_parameters([])

    @classmethod
    def get_circuit_parameters(cls, circuit: Circuit) -> dict[str, dict[str, Any]]:
        return cls._label_parameters(list(_drivers(circuit)))


class LabelWireOut(Component):
    """
    A Wire Source: outputs the signal of the LabelWireIn with the same label.

    Ports:
        <label>: Output, named like the label.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        label: The label.
        width: The number of bits, used when there is no LabelWireIn with the label yet.
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, label: str = "", width: int = 1
    ) -> None:
        driver = _drivers(circuit).get(label)
        width = driver.port_in.width if driver is not None else width
        super().__init__(circuit, name)
        self._label = label
        self._port_out = PortWire(self, self._label, width=width, output=True)
        self.add_port(self._port_out)
        self.parameter_set("label", self._label)
        self.parameter_set("width", width)

    def label(self) -> str:
        """Return Label"""
        return self._label

    @property
    def port_out(self) -> PortWire:
        """The port driven by the LabelWireIn"""
        return self._port_out

    def init(self) -> None:
        if not self._port_out.has_driver():
            driver = _drivers(self.circuit).get(self._label)
            if driver is not None:
                driver.port_in.wire = self._port_out
            else:
                # Not an error: the LabelWireIn can have been deleted in the GUI. The output
                # is then undefined, like an unconnected input.
                warnings.warn(
                    f"LabelWireOut '{self.name()}': no LabelWireIn with the label "
                    f"'{self._label}', the output is undefined",
                    stacklevel=2,
                )
        super().init()

    def remove_connections(self) -> None:
        driver = self._port_out.get_driver()
        if driver is not None:
            driver.disconnect(self._port_out)
        super().remove_connections()

    @classmethod
    def _label_parameters(cls, label_list: list[str]) -> dict[str, dict[str, Any]]:
        return {
            "label": {
                "type": "list",
                "items": label_list,
                "description": "Select label",
            }
        }

    @classmethod
    def get_parameters(cls) -> dict[str, dict[str, Any]]:
        return cls._label_parameters([])

    @classmethod
    def get_circuit_parameters(cls, circuit: Circuit) -> dict[str, dict[str, Any]]:
        return cls._label_parameters(list(_drivers(circuit)))
