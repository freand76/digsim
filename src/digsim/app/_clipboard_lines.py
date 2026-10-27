# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The lines of copied and pasted components (kept free from Qt imports so that it can be
tested without a display)
"""

from __future__ import annotations

from digsim.app._line_graph import through_ports
from digsim.storage_model import LineDataClass


def lines_between(
    lines: list[LineDataClass], ports: set[str], places: dict[str, list[int]]
) -> list[LineDataClass]:
    """
    The parts of lines between some ports ("component.port"), like the ports of copied
    components. A line that goes through another port (its place in 'places') still
    goes through there, the segments that only lead to the other ports go, and a line
    that falls apart is split. A part with fewer than two of the ports connects nothing
    and is left out.
    """
    result: list[LineDataClass] = []
    for line in lines:
        if not ports.intersection(line.ports):
            continue
        result.extend(part for part in through_ports(line, ports, places) if len(part.ports) >= 2)
    return result


def renamed_port(port: str, names: dict[str, str]) -> str:
    """A port ("component.port") of a component that got another name"""
    component, _, name = port.partition(".")
    return f"{names.get(component, component)}.{name}"


def moved_lines(
    lines: list[LineDataClass], names: dict[str, str], dx: int, dy: int
) -> list[LineDataClass]:
    """
    Lines of pasted components: their components have new names ('names', from the
    copied ones), and they are moved by (dx, dy)
    """
    ports = {port for line in lines for port in line.ports}

    def node(name: str) -> str:
        return renamed_port(name, names) if name in ports else name

    return [
        LineDataClass(
            ports=[renamed_port(port, names) for port in line.ports],
            points={key: [point[0] + dx, point[1] + dy] for key, point in line.points.items()},
            segments=[[node(first) for first in segment] for segment in line.segments],
        )
        for line in lines
    ]
