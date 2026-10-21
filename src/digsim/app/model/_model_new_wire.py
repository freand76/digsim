# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Handle new wire object in the model"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF

from digsim.app._wire_path import Point
from digsim.circuit.components.atoms import Component, Port, PortConnectionError


if TYPE_CHECKING:
    from collections.abc import Callable

    from digsim.app._wire_key import Wire
    from digsim.app._wire_lines import At, Node

    from ._model import AppModel


class NewWire:
    """Class to handle functionality for making a new wire"""

    def __init__(self, app_model: AppModel) -> None:
        self._app_model = app_model
        self._start_port: Port | None = None
        self._end_pos: QPointF | None = None
        # The positions clicked between the ports, the wire's corners
        self._clicks: list[Point] = []
        # For a wire started on another wire: that wire, and its corner or a segment and
        # a point on it (a joint there when the wire is finished)
        self._start_branch: tuple[Wire, At] | None = None

    def start_port(self) -> Port | None:
        """Get start port for unfinished new wire object"""
        return self._start_port

    def start_branch(self) -> tuple[Wire, At] | None:
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

    def start_at_corner(self, wire: Wire, at: At) -> None:
        """
        Start a new wire on a drawn wire: at a corner, or at a point on a segment, where
        a joint is added when the wire is finished
        """
        self._start_port = wire[0]
        self._start_branch = (wire, at)
        self._clicks = []

    def end(self, component: Component, portname: str) -> None:
        """End new wire object at a port"""
        end_port = component.port(portname)
        if self._start_port is None:
            raise PortConnectionError("No wire started")
        wires = self._app_model.objects.wires
        if self._start_branch is not None:
            line, corner = self._start_branch
            if end_port.is_output():
                # The output port joins the line, drawn from the line
                self._change(
                    partial(wires.connect_join, end_port, line, corner, self._clicks, False)
                )
            else:
                self._change(partial(wires.connect_branch, line, corner, end_port, self._clicks))
        elif self._start_port.is_output() and end_port.is_input():
            self._change(partial(wires.connect_ports, self._start_port, end_port, self._clicks))
        elif self._start_port.is_input() and end_port.is_output():
            self._change(
                partial(wires.connect_ports, end_port, self._start_port, self._clicks, False)
            )
        else:
            # Two ports of the same kind, their lines become one
            self._change(partial(wires.connect_ports, self._start_port, end_port, self._clicks))

    def can_end_on_wire(self, wire: Wire) -> bool:
        """
        Can the wire end on a drawn wire: if it connects two lines (see ModelWires) of the
        same width. Where it can't, a click there is a corner of the wire.
        """
        if self._start_port is None or self._start_port.width != wire[0].width:
            return False
        start: Node = (
            ("port", self._start_port)
            if self._start_branch is None
            else ("wire", self._start_branch[0])
        )
        return not self._app_model.objects.wires.lines().same(start, ("wire", wire))

    def end_at_corner(self, wire: Wire, corner: int) -> None:
        """End the wire at a corner of a drawn wire"""
        self._end_on_wire(wire, corner)

    def end_at_joint(self, wire: Wire, segment: int, point: Point) -> None:
        """
        End the wire on a segment of a drawn wire: a joint is added there (see
        ModelWires.add_joint), where the wire ends
        """
        self._end_on_wire(wire, (segment, point))

    def _end_on_wire(self, wire: Wire, at: At) -> None:
        """
        A wire from an input port is a branch of the drawn wire, a wire from an output
        port joins its line, and a wire from a corner of another line connects the lines
        """
        if self._start_port is None:
            raise PortConnectionError("No wire started")
        wires = self._app_model.objects.wires
        if self._start_branch is not None:
            self._change(partial(wires.connect_wires, self._start_branch, wire, at, self._clicks))
        elif self._start_port.is_input():
            self._change(
                partial(wires.connect_branch, wire, at, self._start_port, self._clicks, False)
            )
        else:
            self._change(partial(wires.connect_join, self._start_port, wire, at, self._clicks))

    def _change(self, connect: Callable[[], None]) -> None:
        """
        Connect the new wire, an undo step. Raises PortConnectionError, and nothing
        changes, if it can't be connected.
        """
        undo_state = self._app_model.circuit_to_model()
        connect()
        self._app_model.objects.add_undo_state(undo_state)
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
