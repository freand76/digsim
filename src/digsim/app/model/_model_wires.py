# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle the shape of the wires in the model"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

from digsim.app import _wire_tree
from digsim.app._wire_path import (
    X_OFFSET,
    Point,
    arrival_offset,
    automatic_path,
    clicked_path,
    corner_directions,
    corner_points,
    exits_vertically,
    is_forwards,
    is_inner_corner,
    is_valid_path,
    nearest_corner,
    point_on_segment,
    split_corner,
    split_segment,
    step_aside,
)
from digsim.circuit.components.atoms import Port
from digsim.storage_model import GuiWireDataClass


if TYPE_CHECKING:
    from digsim.circuit.components.atoms import Component

    from ._model import AppModel


def port_key(port: Port) -> str:
    """The name of a port in the circuit file, "component.port" """
    return f"{port.parent().name()}.{port.name()}"


class ModelWires:
    """
    The path of every wire, see digsim.app._wire_path. A wire is known by the input port
    it drives, since an input port has one driver. A wire gets the automatic path when it
    is drawn, and keeps its path when components move: only the segments at the ports
    follow them. A wire can start at a corner of another wire from the same output port
    instead of at the port, a branch of a wire tree (see digsim.app._wire_tree).
    """

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._paths: dict[Port, list[float]] = {}
        # Branch: the wire it starts on and the corner it starts at
        self._branches: dict[Port, tuple[Port, int]] = {}

    def clear(self) -> None:
        """Forget all wire paths"""
        self._paths = {}
        self._branches = {}

    def connections(self) -> list[tuple[Port, Port]]:
        """The wires shown in the GUI, (output port, input port)"""
        components = self._app_model.objects.components
        return [
            (src_port, dst_port)
            for component_object in components.get_object_list()
            for src_port in component_object.component.outports()
            for dst_port in src_port.wired_ports
            if dst_port.parent() in components.get_dict()
        ]

    def port_pos(self, port: Port) -> Point:
        """The position of a port in the scene"""
        component_object = self._app_model.objects.components.get_object(port.parent())
        pos = component_object.get_port_item(port).portPos()
        return pos.x(), pos.y()

    def _source(self, dst_port: Port) -> Port:
        src_port = dst_port.get_driver()
        assert src_port is not None
        return src_port

    def branch(self, dst_port: Port) -> tuple[Port, int] | None:
        """The wire that a wire starts on and the corner it starts at, None at the port"""
        return self._branches.get(dst_port)

    def start_point(self, dst_port: Port) -> Point:
        """Where a wire starts: at the output port, or at a corner of another wire"""
        branch = self._branches.get(dst_port)
        if branch is None:
            return self.port_pos(self._source(dst_port))
        parent, corner = branch
        return self.corner_points(parent)[corner]

    def taken_directions(self, wire: Port, corner: int) -> set[str]:
        """The directions that a wire runs in from one of its corners (a branch start)"""
        return corner_directions(self.corner_points(wire), corner)

    def corner_points(self, dst_port: Port) -> list[Point]:
        """The points of a wire, from where it starts to its input port"""
        return corner_points(
            self.start_point(dst_port),
            self.port_pos(dst_port),
            self.path(self._source(dst_port), dst_port),
        )

    def automatic_path(self, src_port: Port, dst_port: Port) -> list[float]:
        """The automatic path of a wire, for the current component positions"""
        if dst_port in self._branches:
            # From the corner where the branch starts, with nothing to run around, and
            # not along the wire it starts on
            start, dest = self.start_point(dst_port), self.port_pos(dst_port)
            taken = self.taken_directions(*self._branches[dst_port])
            if exits_vertically(taken, start, dest):
                if start[0] < dest[0]:
                    return step_aside([start[0]], start, dest, taken)
                return [start[0], math.floor((start[1] + dest[1]) / 2), dest[0] - X_OFFSET]
            if start[0] < dest[0]:
                return [math.floor((start[0] + dest[0]) / 2)]
            return [dest[0] - X_OFFSET]
        component_object = self._app_model.objects.components.get_object(src_port.parent())
        rect = component_object.get_port_item(src_port).portParentRect()
        return automatic_path(
            self.port_pos(src_port),
            self.port_pos(dst_port),
            (rect.x(), rect.y(), rect.width(), rect.height()),
        )

    def path(self, src_port: Port, dst_port: Port) -> list[float]:
        """The path of a wire, a wire without a path gets the automatic path"""
        if dst_port not in self._paths:
            self._paths[dst_port] = self.automatic_path(src_port, dst_port)
        return self._paths[dst_port]

    def new_wire(
        self,
        src_port: Port,
        dst_port: Port,
        clicks: list[Point] | None = None,
        from_source: bool = True,
        branch: tuple[Port, int] | None = None,
    ) -> None:
        """
        Give a new wire its path: through the positions clicked while it was drawn, or the
        automatic path. 'branch' is the wire and corner it starts at, if not at the port.
        """
        # Nothing starts on a new wire (or on an earlier wire to the input port, gone now)
        for child in _wire_tree.children(self._branches, dst_port):
            del self._branches[child]
        self._branches.pop(dst_port, None)
        if branch is not None:
            self._branches[dst_port] = branch
        start, end = self.start_point(dst_port), self.port_pos(dst_port)
        clicks = clicks or []
        if branch is not None:
            # Like it was drawn, a wire from a corner has no component to run around. It
            # leaves or reaches the corner across the other wire, not along it.
            taken = self.taken_directions(*branch)
            if from_source:
                toward = clicks[0] if clicks else end
                vertical_first = exits_vertically(taken, start, toward)
                path = clicked_path(start, end, clicks, vertical_first=vertical_first)
            else:
                offset = arrival_offset(taken, start, clicks[-1] if clicks else end)
                path = clicked_path(start, end, clicks, False, offset)
            path = step_aside(path, start, end, taken)
        elif clicks or is_forwards(start, end):
            path = clicked_path(start, end, clicks, from_source)
        else:
            path = self.automatic_path(src_port, dst_port)
        self._paths[dst_port] = path

    def set_path(
        self,
        dst_port: Port,
        path: list[float],
        corner_map: Callable[[int], int] | None = None,
        undo: bool = True,
    ) -> None:
        """
        Change the path of a wire (an undo step, unless it is part of another one). The
        branches that start on it keep their corner, moved by 'corner_map' when the change
        adds or removes corners, or the corner closest to where they started.
        """
        if not is_valid_path(path):
            raise ValueError(f"Invalid wire path {path}")
        if self._paths.get(dst_port) == path:
            return
        if undo:
            self._app_model.objects.push_undo_state()
        children = _wire_tree.children(self._branches, dst_port)
        old_points = self.corner_points(dst_port) if children else []
        old_length = len(self._paths.get(dst_port, path))
        self._paths[dst_port] = list(path)
        for child in children:
            corner = self._branches[child][1]
            if corner_map is not None:
                corner = corner_map(corner)
            elif len(path) != old_length:
                start = self.start_point(dst_port)
                corner = nearest_corner(start, self.port_pos(dst_port), path, old_points[corner])
            self._branches[child] = (dst_port, corner)
        self._app_model.model_changed()

    def move_paths(self, paths: dict[Port, list[float]], dx: int, dy: int) -> None:
        """
        Give wires their paths moved by (dx, dy), while components that they run between
        are moved together (part of the move's undo step)
        """
        for dst_port, path in paths.items():
            self._paths[dst_port] = [
                value + (dy if index % 2 else dx) for index, value in enumerate(path)
            ]

    def add_joint(self, dst_port: Port, segment: int, point: Point, undo: bool = True) -> int:
        """
        Add a joint to a segment of a wire, at the point of the segment closest to 'point':
        a corner, where a branch can start, that keeps the wire's shape. Returns the corner.
        """
        start, end = self.start_point(dst_port), self.port_pos(dst_port)
        path = self.path(self._source(dst_port), dst_port)
        at = point_on_segment(start, end, path, segment, point)
        new_path = split_segment(start, end, path, segment, at, step_size=0)
        self.set_path(dst_port, new_path, partial(split_corner, segment), undo)
        return segment + 1

    def tree(self, dst_port: Port) -> list[Port]:
        """All wires from the same output port, that start on each other"""
        return _wire_tree.tree(self._branches, dst_port)

    def route(self, dst_port: Port) -> dict[Port, int | None]:
        """The wires on the way from the output port, see _wire_tree.route()"""
        return _wire_tree.route(self._branches, dst_port)

    def sinks_through(self, dst_port: Port, segment: int) -> list[Port]:
        """The wires whose way to their input port runs through a segment of a wire"""
        return _wire_tree.sinks_through(self._branches, dst_port, segment)

    def selection(self, dst_port: Port, segment: int) -> dict[Port, int]:
        """The part of a tree that a click on a segment selects, see _wire_tree.selection()"""
        return _wire_tree.selection(self._branches, dst_port, segment)

    def _remove(self, dst_ports: list[Port]) -> None:
        """
        Forget wires, before they are disconnected, and keep the wires that start on them
        """
        _wire_tree.remove_wires(
            self._branches,
            self._paths,
            dst_ports,
            lambda wire, corner: self.corner_points(wire)[corner],
        )

    def delete_wires(self, dst_ports: list[Port]) -> None:
        """Delete the wires to some input ports"""
        self._remove(dst_ports)
        for dst_port in dst_ports:
            self._source(dst_port).disconnect(dst_port)

    def remove_component(self, component: Component) -> None:
        """Forget the wires of a component that is deleted, before it is disconnected"""
        self._remove(
            [
                dst_port
                for src_port, dst_port in self.connections()
                if component in (src_port.parent(), dst_port.parent())
            ]
        )

    def from_dict(self, wires: dict[str, GuiWireDataClass]) -> None:
        """
        Set the paths from a circuit file, after the components are placed. Wires without
        a valid path in the file get the automatic path, and wires that can't start where
        the file says start at the output port.
        """
        self.clear()
        connections = self.connections()
        dst_ports = {port_key(dst_port): dst_port for _, dst_port in connections}
        for src_port, dst_port in connections:
            wire_dc = wires.get(port_key(dst_port))
            path: list[float] = list(wire_dc.path) if wire_dc is not None else []
            if is_valid_path(path):
                self._paths[dst_port] = path
            else:
                self._paths[dst_port] = self.automatic_path(src_port, dst_port)
        branches = {}
        for src_port, dst_port in connections:
            wire_dc = wires.get(port_key(dst_port))
            if wire_dc is None or wire_dc.branch is None or wire_dc.corner is None:
                continue
            parent = dst_ports.get(wire_dc.branch)
            if (
                parent is not None
                and parent.get_driver() is src_port
                and is_inner_corner(self._paths[parent], wire_dc.corner)
            ):
                branches[dst_port] = (parent, wire_dc.corner)
        self._branches = _wire_tree.without_cycles(branches)

    def to_dict(self) -> dict[str, GuiWireDataClass]:
        """The path of every wire, and where it starts, for the circuit file"""
        wires = {}
        for src_port, dst_port in self.connections():
            branch = self._branches.get(dst_port)
            wires[port_key(dst_port)] = GuiWireDataClass(
                path=[round(value) for value in self.path(src_port, dst_port)],
                branch=None if branch is None else port_key(branch[0]),
                corner=None if branch is None else branch[1],
            )
        return wires
