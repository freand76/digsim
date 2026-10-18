# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle new wire object in the model"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF

from digsim.app._wire_path import Point
from digsim.circuit.components.atoms import Component, Port, PortConnectionError


if TYPE_CHECKING:
    from ._model import AppModel


class NewWire:
    """Class to handle functionality for making a new wire"""

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._start_port: Port | None = None
        self._end_pos: QPointF | None = None
        # The positions clicked between the ports, the wire's corners
        self._clicks: list[Point] = []
        # For a wire started at a corner of another wire: that wire and the corner
        self._start_branch: tuple[Port, int] | None = None

    def start_port(self) -> Port | None:
        """Get start port for unfinished new wire object"""
        return self._start_port

    def start_branch(self) -> tuple[Port, int] | None:
        """The wire and corner where the new wire started, None if it started at a port"""
        return self._start_branch

    def end_pos(self) -> QPointF | None:
        """Get end point for unfinished new wire object"""
        return self._end_pos

    def clicks(self) -> list[Point]:
        """The positions clicked since the wire was started"""
        return self._clicks

    def add_click(self, pos: QPointF) -> None:
        """A click between the ports: a corner, where the wire turns vertical"""
        self._clicks.append((round(pos.x()), round(pos.y())))

    def remove_last_click(self) -> None:
        """Remove the last corner, to correct a click"""
        if len(self._clicks) > 0:
            self._clicks.pop()

    def start(self, component: Component, portname: str) -> None:
        """Start new wire object"""
        if component.port(portname).can_add_wire():
            self._start_port = component.port(portname)
            self._start_branch = None
            self._clicks = []

    def start_at_corner(self, wire: Port, corner: int) -> None:
        """
        Start a new wire at a corner of the wire to the input port 'wire', a branch of
        the wire tree from the same output port
        """
        self._start_port = wire.get_driver()
        self._start_branch = (wire, corner)
        self._clicks = []

    def end(self, component: Component, portname: str) -> None:
        """End new wire object"""
        end_port = component.port(portname)
        if self._start_port is None:
            raise PortConnectionError("No wire started")
        if self._start_branch is not None and not end_port.is_input():
            raise PortConnectionError("A wire from a wire must end at an input port")
        if self._start_port.is_output() and end_port.is_input():
            src_port, dst_port = self._start_port, end_port
        elif self._start_port.is_input() and end_port.is_output():
            src_port, dst_port = end_port, self._start_port
        else:
            raise PortConnectionError("Cannot connect to port of same type")
        self._connect(src_port, dst_port, self._start_branch)

    def can_end_at_corner(self) -> bool:
        """Can the wire end at a corner of another wire: if it was started at an input port"""
        return (
            self._start_port is not None
            and self._start_branch is None
            and self._start_port.is_input()
        )

    def end_at_corner(self, wire: Port, corner: int) -> None:
        """
        End a wire drawn from an input port at a corner of the wire to the input port
        'wire', a branch of the wire tree from that wire's output port
        """
        if self._start_port is None:
            raise PortConnectionError("No wire started")
        if not self.can_end_at_corner():
            raise PortConnectionError("A wire to a wire must start at an input port")
        src_port = wire.get_driver()
        if src_port is None:
            raise PortConnectionError("The wire has no output port")
        self._connect(src_port, self._start_port, (wire, corner))

    def end_at_joint(self, wire: Port, segment: int, point: Point) -> None:
        """
        End a wire drawn from an input port on a segment of the wire to the input port
        'wire': a joint is added there (see ModelWires.add_joint), where the wire starts
        """
        if self._start_port is None:
            raise PortConnectionError("No wire started")
        if not self.can_end_at_corner():
            raise PortConnectionError("A wire to a wire must start at an input port")
        src_port = wire.get_driver()
        if src_port is None:
            raise PortConnectionError("The wire has no output port")
        self._connect(src_port, self._start_port, None, joint=(wire, segment, point))

    def _connect(
        self,
        src_port: Port,
        dst_port: Port,
        branch: tuple[Port, int] | None,
        joint: tuple[Port, int, Point] | None = None,
    ) -> None:
        undo_state = self._app_model.circuit_to_model()
        # Raises PortConnectionError if the ports can't be connected: nothing to undo then
        src_port.wire = dst_port
        self._app_model.objects.add_undo_state(undo_state)
        if joint is not None:
            # In the same undo step as the new wire
            wire, segment, point = joint
            branch = (wire, self._app_model.objects.wires.add_joint(wire, segment, point, False))
        self._app_model.objects.wires.new_wire(
            src_port,
            dst_port,
            self._clicks,
            from_source=src_port is self._start_port,
            branch=branch,
        )
        self._app_model.sig_update_wires.emit()
        self._app_model.model_changed()
        self.abort()

    def abort(self) -> None:
        """Abort new wire object"""
        self._start_port = None
        self._start_branch = None
        self._end_pos = None
        self._clicks = []

    def set_end_pos(self, pos: QPointF) -> None:
        """Update end point for unfinished new wire object"""
        self._end_pos = pos

    def ongoing(self) -> bool:
        """Return True if an unfinished new wire object is active"""
        return self._start_port is not None
