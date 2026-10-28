# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""A bus split into groups of bits, or groups of bits merged into a bus"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import (
    VALUE_TYPE,
    Component,
    ComponentException,
    Parameter,
    Port,
    PortMultiBitWire,
    PortWire,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit

# The widest bus
MAX_WIDTH = 32


def group_ranges(groups: list[int]) -> list[tuple[int, int]]:
    """The (msb, lsb) of each group, the first group from bit 0"""
    ranges = []
    lsb = 0
    for width in groups:
        ranges.append((lsb + width - 1, lsb))
        lsb += width
    return ranges


def group_name(msb: int, lsb: int) -> str:
    """The port name of a group: bus_5 for one bit, bus_7_4 for bits 7 to 4"""
    return f"bus_{lsb}" if msb == lsb else f"bus_{msb}_{lsb}"


def group_text(groups: list[int]) -> str:
    """The groups as the text of the settings: 4, 4"""
    return ", ".join(str(width) for width in groups)


def parse_groups(text: str) -> list[int]:
    """
    The widths of the groups from a text like "4, 4" or "1 3 4", the first from bit 0.
    Raises ComponentException if it isn't groups of a bus with 2 to 32 bits.
    """
    try:
        groups = [int(part) for part in text.replace(",", " ").split()]
    except ValueError as exc:
        raise ComponentException("The groups are widths, like 4, 4") from exc
    _check_groups(groups)
    return groups


def _check_groups(groups: list[int]) -> None:
    if len(groups) < 2:
        raise ComponentException("A splitter has at least two groups")
    if any(width < 1 for width in groups):
        raise ComponentException("A group has at least one bit")
    if sum(groups) > MAX_WIDTH:
        raise ComponentException(f"The bus has at most {MAX_WIDTH} bits")


class _GroupPort(PortWire):
    """A group of bits of a bus, it updates the bus when it changes"""

    def __init__(self, parent: Component, bus: _GroupBus, msb: int, lsb: int, output: bool):
        super().__init__(parent, group_name(msb, lsb), msb - lsb + 1, output)
        self._bus = bus
        self.lsb = lsb

    def set_value(self, value: VALUE_TYPE) -> None:
        super().set_value(value)
        self._bus.update_value_from_bits()


class _GroupBus(PortMultiBitWire):
    """A bus made of groups of bits, like PortMultiBitWire is made of single bits"""

    def __init__(self, parent: Component, groups: list[int], output: bool) -> None:
        # Not PortMultiBitWire.__init__(), which makes a port for each bit
        self._port_driver = None
        self._groups: list[_GroupPort] = []
        Port.__init__(self, parent, "bus", sum(groups), output)
        self._groups = [
            _GroupPort(parent, self, msb, lsb, output=not output)
            for msb, lsb in group_ranges(groups)
        ]

    def init(self) -> None:
        Port.init(self)
        for group in self._groups:
            group.init()

    @property
    def groups(self) -> list[Port]:
        """The ports of the groups, the first from bit 0"""
        return list(self._groups)

    def set_value(self, value: VALUE_TYPE) -> None:
        for group in self._groups:
            if isinstance(value, str):
                group.value = value
            else:
                group.value = (value >> group.lsb) & ((1 << group.width) - 1)

    def get_wired_ports_recursive(self, processed_ports: set[Port] | None = None) -> list[Port]:
        if processed_ports is None:
            processed_ports = set()
        all_wired_ports = Port.get_wired_ports_recursive(self, processed_ports)
        for group in self._groups:
            all_wired_ports.extend(group.get_wired_ports_recursive(processed_ports))
        return all_wired_ports

    def get_bit(self, bit_id: int) -> Port:
        raise ComponentException("A splitter has groups, not bits")

    def update_value_from_bits(self) -> None:
        """Update the bus with the value of the groups"""
        value = 0
        not_driven = 0
        for group in self._groups:
            group_value = group.value
            if group_value == "X":
                bus_value: VALUE_TYPE = "X"
                break
            if group_value == "Z":
                not_driven += 1
                continue
            value |= group_value << group.lsb
        else:
            # Not driven if no group is, and undefined if only some are
            if not not_driven:
                bus_value = value
            else:
                bus_value = "Z" if not_driven == len(self._groups) else "X"
        if bus_value != self._value:
            self.update_wires(bus_value)
            # The event updates the waves
            self.parent().add_event(self, bus_value, 0)


class Splitter(Component):
    """
    Splits a bus into groups of bits, like [7:4] and [3:0], or merges groups into a bus.

    Ports:
        bus: The bus, `sum(groups)` bits. An input when splitting, an output when merging.
        bus_3_0, bus_7_4, ...: The groups, from bit 0. A group of one bit is bus_5.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        groups: The width of each group, the first from bit 0. [4, 4] splits 8 bits into
            bus_3_0 and bus_7_4.
        direction: "split" (bus in, groups out) or "merge" (groups in, bus out).
    """

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        groups: list[int] | None = None,
        direction: str = "split",
    ) -> None:
        super().__init__(circuit, name)
        groups = list(groups) if groups is not None else [4, 4]
        _check_groups(groups)
        if direction not in ("split", "merge"):
            raise ComponentException(f"The direction is split or merge, not '{direction}'")
        self._bus = _GroupBus(self, groups, output=direction == "merge")
        self.add_port(self._bus)
        for group in self._bus.groups:
            self.add_port(group)
        self.parameter_set("groups", groups)
        self.parameter_set("direction", direction)

    @property
    def groups(self) -> list[Port]:
        """The ports of the groups, the first from bit 0"""
        return self._bus.groups

    def group_ranges(self) -> list[tuple[int, int]]:
        """The (msb, lsb) of each group, the first from bit 0"""
        return group_ranges(self.parameter_get("groups"))

    def is_merge(self) -> bool:
        """True if the groups are merged into the bus, False if the bus is split"""
        return self.parameter_get("direction") == "merge"

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "groups": {
                "type": "bit_groups",
                "default": [4, 4],
                "description": "Group widths, from bit 0",
            },
            "direction": {
                "type": "list",
                "items": ["split", "merge"],
                "default": "split",
                "description": "Split the bus into groups, or merge groups into a bus",
            },
        }
