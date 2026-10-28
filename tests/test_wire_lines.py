# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the lines of the wires drawn in the GUI, with every wire on them"""

import pytest

from digsim.app._line_graph import on_segment
from digsim.app._wire_key import drawn_key, wire_key
from digsim.app._wire_lines import PointMove, WireDrawing
from digsim.app._wire_path import corner_points
from digsim.app._wire_route import rotated
from digsim.circuit import Circuit
from digsim.circuit.components import (
    Led,
    OnOffSwitch,
    PortConnectionError,
    PortInOut,
    PushButton,
    StaticValue,
)
from digsim.circuit.components.atoms import Component, PortOutImmediate
from digsim.storage_model import GuiWireDataClass, LineDataClass


class Transceiver(Component):
    """A component with an inout port, IO, and a value that it drives on it"""

    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(PortInOut(self, "IO"))
        # Not a port of the component, so not a wire of the drawing
        self._drive = PortOutImmediate(self, "drive")
        self._drive.wire = self.IO.get_drive_bit(0)

    def drive(self, value):
        """Drive a value on IO, "Z" to let go of it"""
        self._drive.value = value


class Drawing(WireDrawing):
    """The wires of a circuit, with each component at its place (x, y)"""

    def __init__(self) -> None:
        super().__init__()
        self.circuit = Circuit()
        self.places = {}

    def add(self, component, x, y):
        self.places[component] = (x, y)
        return component

    def button(self, name, x, y):
        return self.add(PushButton(self.circuit, name), x, y).O

    def led(self, name, x, y):
        return self.add(Led(self.circuit, name), x, y).I

    def transceiver(self, name, x, y):
        return self.add(Transceiver(self.circuit, name), x, y).IO

    def connections(self):
        return [
            (src_port, dst_port)
            for component in self.circuit.get_toplevel_components()
            for src_port in component.outports()
            for dst_port in src_port.wired_ports
        ]

    def ports(self):
        return [
            port
            for component in self.circuit.get_toplevel_components()
            for port in component.ports
        ]

    def port_pos(self, port):
        x, y = self.places[port.parent()]
        # Outputs on the right side of the component, inputs on the left
        return (x + 40, y) if port.is_output() else (x, y)

    def port_rect(self, port):
        x, y = self.places[port.parent()]
        return x, y - 20, 40, 40

    def drivers(self, port):
        return sorted(driver.parent().name() for driver in port.get_drivers())

    def keys(self):
        """The drawn and the implied wires"""
        return (
            sorted(drawn_key(wire) for wire in self.drawn()),
            sorted(wire_key(wire) for wire in self.connections() if self.is_implied(wire)),
        )


def middle(drawing, wire, segment):
    """The middle of a segment of a drawn wire"""
    points = drawing.corner_points(wire)
    (x1, y1), (x2, y2) = points[segment], points[segment + 1]
    return segment, ((x1 + x2) / 2, (y1 + y2) / 2)


@pytest.fixture(name="bus")
def fixture_bus():
    """
    A line from button A to LED 1, with a branch to LED 2, and button B that joins it:
    B's wire ends on A's wire to LED 1
    """
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 300)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    drawing.connect_branch((a, led1), middle(drawing, (a, led1), 1), led2)
    drawing.connect_join(b, (a, led1), middle(drawing, (a, led1), 2))
    return drawing, a, b, led1, led2


def test_ports_and_branch():
    """A wire between two ports, and a branch of it to another input port"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    assert drawing.corner_points((a, led1)) == [(40, 0), (390, 0), (390, 100), (400, 100)]
    drawing.connect_branch((a, led1), middle(drawing, (a, led1), 1), led2)
    assert drawing.branch((a, led2)) == ((a, led1), 2)
    assert drawing.corner_points((a, led2))[0] == (390, 50)
    assert drawing.keys() == (["L1.I", "L2.I"], [])
    line = drawing.line(("port", a))
    assert line.outputs == [a]
    assert line.inputs == [led1, led2]


def test_joined_output_drives_the_line(bus):
    """An output that joins a line drives all its inputs, with one drawn wire"""
    drawing, a, b, led1, led2 = bus
    assert drawing.join((b, led1)) == ((a, led1), 3)
    assert drawing.corner_points((b, led1))[-1] == drawing.corner_points((a, led1))[3]
    assert drawing.keys() == (["L1.I<A.O", "L1.I<B.O", "L2.I<A.O"], ["L2.I<B.O"])
    assert drawing.drivers(led2) == ["A", "B"]


def test_line_values(bus):
    """Every output drives every input: different values give "X\""""
    drawing, a, b, led1, led2 = bus
    drawing.circuit.init()
    drawing.circuit.run(ns=10)
    assert (led1.value, led2.value) == (0, 0)
    a.parent().push()
    drawing.circuit.run(ns=10)
    assert (led1.value, led2.value) == ("X", "X")
    b.parent().push()
    drawing.circuit.run(ns=10)
    assert (led1.value, led2.value) == (1, 1)


def test_branch_on_a_joined_wire(bus):
    """An input port on the wire of a joined output is on the line: all outputs drive it"""
    drawing, a, b, led1, _ = bus
    led3 = drawing.led("L3", 400, 300)
    drawing.connect_branch((b, led1), middle(drawing, (b, led1), 0), led3)
    assert drawing.branch((b, led3)) == ((b, led1), 1)
    assert drawing.drivers(led3) == ["A", "B"]
    assert drawing.is_implied((a, led3))


def test_join_a_joined_wire(bus):
    """An output that joins the wire of a joined output drives the whole line"""
    drawing, _, b, led1, led2 = bus
    c = drawing.button("C", 0, 400)
    drawing.connect_join(c, (b, led1), middle(drawing, (b, led1), 0))
    assert drawing.join((c, led1)) == ((b, led1), 1)
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A", "B", "C"]


def test_new_branch_of_the_line(bus):
    """A branch added to the line is driven by the joined outputs too"""
    drawing, a, _, led1, _ = bus
    led3 = drawing.led("L3", 400, 300)
    drawing.connect_branch((a, led1), 2, led3, from_source=False)
    assert drawing.drivers(led3) == ["A", "B"]


def test_ports_connect_lines():
    """A wire between ports of two lines makes them one line"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 200)
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    drawing.connect_ports(b, led2)
    drawing.connect_ports(b, led1, from_source=False)
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A", "B"]
    assert drawing.keys() == (["L1.I<A.O", "L1.I<B.O", "L2.I<B.O"], ["L2.I<A.O"])


def test_wire_between_lines():
    """A wire from a corner of one line to another line makes them one line"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 200)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 300)
    drawing.connect_ports(a, led1)
    drawing.connect_ports(b, led2)
    drawing.connect_wires(((a, led1), 1), (b, led2), middle(drawing, (b, led2), 1))
    wire = (a, led2)
    assert drawing.branch(wire) == ((a, led1), 1)
    assert drawing.join(wire) == ((b, led2), 2)
    assert drawing.corner_points(wire)[0] == drawing.corner_points((a, led1))[1]
    assert drawing.corner_points(wire)[-1] == drawing.corner_points((b, led2))[2]
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A", "B"]


def test_same_line_is_refused(bus):
    """A new wire must connect two lines: nothing changes otherwise"""
    drawing, a, b, led1, led2 = bus
    before = drawing.to_dict()
    with pytest.raises(PortConnectionError, match="same line"):
        drawing.connect_join(b, (a, led2), 1)
    with pytest.raises(PortConnectionError, match="same line"):
        drawing.connect_ports(a, led2)
    with pytest.raises(PortConnectionError, match="same line"):
        drawing.connect_branch((b, led1), 1, led2)
    assert drawing.to_dict() == before


def test_width_is_refused(bus):
    """A bus can't join a line of single bits"""
    drawing, a, _, led1, _ = bus
    value = drawing.add(StaticValue(drawing.circuit, "V", width=4), 0, 500).O
    before = drawing.to_dict()
    with pytest.raises(PortConnectionError, match="different widths"):
        drawing.connect_join(value, (a, led1), 1)
    assert drawing.to_dict() == before
    assert value.wired_ports == []


def test_delete_a_joined_wire(bus):
    """The joined output drives nothing when its wire is gone"""
    drawing, _, b, led1, led2 = bus
    drawing.delete_wires([(b, led1)])
    assert b.wired_ports == []
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A"]
    assert drawing.keys() == (["L1.I", "L2.I"], [])


def test_delete_a_branch_of_the_line(bus):
    """An input port that the line doesn't reach any more is driven by none of its outputs"""
    drawing, a, _, led1, led2 = bus
    drawing.delete_wires([(a, led2)])
    assert drawing.drivers(led2) == []
    assert drawing.drivers(led1) == ["A", "B"]
    assert drawing.keys() == (["L1.I<A.O", "L1.I<B.O"], [])


def test_delete_the_wire_a_joined_wire_ends_on():
    """Without a wire where it ended, a joined wire goes too, with its connections"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 300)
    led = drawing.led("L", 400, 100)
    drawing.connect_ports(a, led)
    drawing.connect_join(b, (a, led), middle(drawing, (a, led), 1))
    drawing.delete_wires([(a, led)])
    assert drawing.connections() == []


def test_joined_wire_ends_on_the_wire_that_runs_there(bus):
    """
    When the wire where a joined wire ends is deleted, the branch that takes its place
    runs there: the joined wire ends on it
    """
    drawing, a, b, led1, led2 = bus
    point = drawing.corner_points((b, led1))[-1]
    drawing.delete_wires([(a, led1)])
    # The branch to LED 2 starts at the port now, and runs where B's wire ended
    assert drawing.branch((a, led2)) is None
    assert drawing.join((b, led1)) is None
    host, corner = drawing.join((b, led2))
    assert host == (a, led2)
    assert drawing.corner_points(host)[corner] == point
    assert drawing.drivers(led1) == []
    assert drawing.drivers(led2) == ["A", "B"]


def test_delete_the_input_a_joined_wire_is_known_by(bus):
    """A joined wire is known by another input port of the line when its own one is gone"""
    drawing, _, b, led1, led2 = bus
    drawing.remove_component(led1.parent())
    drawing.circuit.delete_component(led1.parent())
    assert drawing.join((b, led2)) is not None
    assert drawing.keys() == (["L2.I<A.O", "L2.I<B.O"], [])
    assert drawing.drivers(led2) == ["A", "B"]


def test_delete_an_output_of_the_line(bus):
    """The other outputs of a line keep driving it"""
    drawing, _, b, led1, led2 = bus
    c = drawing.button("C", 0, 400)
    drawing.connect_join(c, (b, led1), middle(drawing, (b, led1), 0))
    drawing.remove_component(b.parent())
    drawing.circuit.delete_component(b.parent())
    # C's wire ended on B's wire: it went too
    assert c.wired_ports == []
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A"]


def test_save_and_load(bus):
    """The drawn wires, where they start and end, and the implied wires are saved"""
    drawing, *_ = bus
    saved = drawing.to_dict()
    assert saved["L2.I<B.O"] == GuiWireDataClass(path=[], drawn=False)
    assert saved["L1.I<B.O"].joint == "L1.I<A.O"
    assert saved["L1.I<B.O"].joint_corner == 3
    shape = {wire: drawing.corner_points(wire) for wire in drawing.drawn()}
    drawing.from_dict(saved)
    assert drawing.to_dict() == saved
    assert {wire: drawing.corner_points(wire) for wire in drawing.drawn()} == shape


def test_load_joins_of_the_first_format(bus):
    """
    The first files with joined wires stored them like a branch, with one wire for each
    input port of the line
    """
    drawing, a, b, led1, led2 = bus
    saved = drawing.to_dict()
    joined = saved["L1.I<B.O"]
    old = GuiWireDataClass(path=joined.path, branch="L1.I<A.O", corner=3)
    saved["L1.I<B.O"] = old
    saved["L2.I<B.O"] = old
    drawing.from_dict(saved)
    assert drawing.join((b, led1)) == ((a, led1), 3)
    assert drawing.is_implied((b, led2))


def test_load_implied_wire_without_line():
    """A wire that the file says isn't drawn, but that no line implies, is drawn"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led = drawing.led("L", 400, 0)
    a.wire = led
    drawing.from_dict({"L.I": GuiWireDataClass(path=[], drawn=False)})
    assert drawing.drawn() == [(a, led)]
    assert drawing.path((a, led)) == drawing.automatic_path((a, led))


def test_wire_between_inputs():
    """A wire between two input ports puts them on one line, without a driver at first"""
    drawing = Drawing()
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(led1, led2)
    assert drawing.drawn() == [(led1, led2)]
    assert drawing.drivers(led1) == drawing.drivers(led2) == []
    # An output on the line drives both
    a = drawing.button("A", 0, 0)
    drawing.connect_ports(a, led1)
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A"]
    assert drawing.keys() == (["L1.I", "L2.I<L1.I"], ["L2.I"])


def test_wire_between_outputs():
    """A wire between two output ports makes their lines one"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 200)
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    drawing.connect_ports(b, led2)
    drawing.connect_ports(a, b)
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A", "B"]
    assert (a, b) in drawing.drawn()


def test_same_port_is_refused():
    """A wire can't end where it starts"""
    drawing = Drawing()
    led = drawing.led("L", 400, 0)
    with pytest.raises(PortConnectionError, match="where it starts"):
        drawing.connect_ports(led, led)


def test_join_a_wire_between_inputs():
    """An output that joins a wire between two inputs drives both"""
    drawing = Drawing()
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(led1, led2)
    b = drawing.button("B", 0, 300)
    drawing.connect_join(b, (led1, led2), middle(drawing, (led1, led2), 1))
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["B"]
    assert drawing.join((b, led2)) is not None


def test_delete_a_wire_between_inputs():
    """The input that the line doesn't reach any more isn't driven"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    drawing.connect_ports(led1, led2)
    drawing.delete_wires([(led1, led2)])
    assert drawing.drivers(led1) == ["A"]
    assert drawing.drivers(led2) == []
    assert drawing.drawn() == [(a, led1)]


def test_save_and_load_a_wire_between_inputs():
    """A wire that is no connection is saved by both its ports"""
    drawing = Drawing()
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(led1, led2, clicks=[(450, 100)])
    saved = drawing.to_dict()
    assert list(saved) == ["L2.I<L1.I"]
    shape = drawing.corner_points((led1, led2))
    drawing.from_dict(saved)
    assert drawing.drawn() == [(led1, led2)]
    assert drawing.corner_points((led1, led2)) == shape


def test_branch_to_a_port_beside_the_corner():
    """A branch to a port just beside its corner leaves the corner across the wire"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 200)
    led2 = drawing.led("L2", 400, 100)
    drawing.connect_ports(a, led1)
    # A joint on the vertical part, 10 to the left of LED 2's port
    drawing.connect_branch((a, led1), (1, (390, 150)), led2)
    points = drawing.corner_points((a, led2))
    assert points[0] == (390, 150)
    assert points[1] == (395, 150)


@pytest.mark.parametrize(
    "first, second, expected", [(False, False, 0), (True, True, 1), (True, False, "X")]
)
def test_value_of_a_wire_between_outputs(first, second, expected):
    """
    A wire between two switch outputs has the value that they drive together: off, on,
    or undefined when one is on and the other off. It has no input that gets the value.
    """
    drawing = Drawing()
    switches = [drawing.add(OnOffSwitch(drawing.circuit, f"S{i}"), 0, 100 * i) for i in range(2)]
    drawing.connect_ports(switches[0].O, switches[1].O)
    drawing.circuit.init()
    for switch, on in zip(switches, (first, second), strict=True):
        if on:
            switch.turn_on()
    drawing.circuit.run(ns=10)
    wire = (switches[0].O, switches[1].O)
    assert drawing.line_value(wire) == expected
    assert drawing.value(drawing.line_outputs()[wire]) == expected


def test_value_of_a_line_without_outputs():
    """A wire between two inputs, that no output drives, is not driven"""
    drawing = Drawing()
    led1 = drawing.led("L1", 400, 0)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(led1, led2)
    assert drawing.line_value((led1, led2)) == "Z"


def shape(drawing):
    """The lines of a drawing as sets of segments between places, and their ports"""
    shapes = set()
    for line in drawing.to_lines():
        ports = {f"{port.parent().name()}.{port.name()}": port for port in drawing.ports()}

        def place(node, line=line, ports=ports):
            if node in ports:
                return drawing.port_pos(ports[node])
            return tuple(line.points[node])

        segments = frozenset(frozenset((place(a), place(b))) for a, b in line.segments)
        shapes.add((frozenset(line.ports), segments))
    return shapes


def round_trip(drawing):
    """
    Save the lines and load them again: the same lines, the same connections. The drawn
    wires can be others (a joined wire can be a branch then), the next time they are the
    same.
    """
    before = shape(drawing)
    connections = set(drawing.connections())
    drawing.from_lines(drawing.to_lines())
    assert shape(drawing) == before
    assert set(drawing.connections()) == connections
    for wire in drawing.connections():
        assert drawing.is_connected(wire)
    lines = drawing.to_lines()
    drawing.from_lines(lines)
    assert drawing.to_lines() == lines


def test_lines_of_a_bus(bus):
    """The bus as a graph: B's wire ends where the branch to LED 2 starts"""
    drawing, *_ = bus
    (line,) = drawing.to_lines()
    assert line.ports == ["A.O", "L1.I", "L2.I", "B.O"]
    joint = next(node for node, point in line.points.items() if point == [390, 50])
    assert sum(joint in segment for segment in line.segments) == 4
    assert all(
        line.points.get(a, [0, 0])[0] == line.points.get(b, [1, 0])[0]
        or line.points.get(a, [0, 0])[1] == line.points.get(b, [0, 1])[1]
        for a, b in line.segments
        if a in line.points and b in line.points
    )
    round_trip(drawing)


def test_lines_round_trip(bus):
    """Every kind of wire: branches, joins, wires between lines and between inputs"""
    drawing, a, b, led1, _ = bus
    led3 = drawing.led("L3", 400, 300)
    drawing.connect_branch((b, led1), middle(drawing, (b, led1), 0), led3)
    c = drawing.button("C", 0, 400)
    drawing.connect_join(c, (b, led1), middle(drawing, (b, led1), 0))
    d = drawing.button("D", 0, 500)
    led4 = drawing.led("L4", 400, 500)
    drawing.connect_ports(d, led4, clicks=[(150, 520)])
    drawing.connect_wires(((d, led4), 1), (a, led1), middle(drawing, (a, led1), 0))
    led5 = drawing.led("L5", 400, 600)
    led6 = drawing.led("L6", 400, 700)
    drawing.connect_ports(led5, led6)
    round_trip(drawing)


def test_lines_of_wires_drawn_twice():
    """Two outputs each drawn to the same two inputs: a loop, cut, the line stays"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 300)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 200)
    for src_port in (a, b):
        for dst_port in (led1, led2):
            src_port.wire = dst_port
    drawing.from_dict({})
    drawing.from_lines(drawing.to_lines())
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["A", "B"]
    for wire in drawing.connections():
        assert drawing.is_connected(wire)
    lines = drawing.to_lines()
    drawing.from_lines(lines)
    assert drawing.to_lines() == lines


def test_delete_a_branch_removes_its_joint():
    """The joint where a deleted branch started goes too, the wire keeps its shape"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    path = list(drawing.path((a, led1)))
    drawing.connect_branch((a, led1), middle(drawing, (a, led1), 1), led2)
    assert drawing.path((a, led1)) != path
    drawing.delete_wires([(a, led2)])
    assert drawing.path((a, led1)) == path


def test_delete_keeps_the_joints_in_use(bus):
    """A joint that another wire still starts or ends on stays"""
    drawing, a, b, led1, led2 = bus
    corner = drawing.join((b, led1))[1]
    drawing.delete_wires([(a, led2)])
    assert drawing.join((b, led1)) is not None
    host, at = drawing.join((b, led1))
    assert drawing.corner_points(host)[at] == drawing.corner_points((b, led1))[-1]
    assert at <= corner


def test_move_a_joint():
    """A joint moves along its wire, between its corners, and its branch goes with it"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 200)
    drawing.connect_ports(a, led1)
    # A joint on the first horizontal run, from (40, 0) to (390, 0), and a branch down
    drawing.connect_branch((a, led1), (0, (200, 0)), led2, clicks=[(200, 200)])
    wire, branch = (a, led1), (a, led2)
    assert drawing.corner_points(branch)[:2] == [(200, 0), (200, 0)]
    move = drawing.point_move((200, 0))
    assert move == PointMove(wire, 1, (41, 389))
    drawing.move_point(move, 120)
    assert drawing.corner_points(wire)[1] == (120, 0)
    # The branch still leaves down, from the joint
    assert drawing.corner_points(branch)[:3] == [(120, 0), (120, 0), (120, 200)]
    # Not past the corners
    move = drawing.point_move((120, 0))
    assert move is not None
    drawing.move_point(move, 1000)
    assert drawing.corner_points(wire)[1] == (389, 0)


def test_move_a_point_at_a_corner():
    """
    A wire turns at a corner, and a branch from the corner goes on straight: the point
    moves along the straight line, the segment of the corner across moves with it
    """
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 600, 0)
    drawing.connect_ports(a, led1)
    wire = (a, led1)
    assert drawing.corner_points(wire) == [(40, 0), (390, 0), (390, 100), (400, 100)]
    drawing.connect_branch(wire, 1, led2)
    branch = (a, led2)
    assert drawing.corner_points(branch)[0] == (390, 0)
    move = drawing.point_move((390, 0))
    assert move is not None
    assert move.wire == wire and move.segment == 1
    # From the output port on the left to the branch's next corner on the right
    low, high = move.bounds
    assert low == 41
    assert high > 390
    drawing.move_point(move, 300)
    assert drawing.corner_points(wire)[1:3] == [(300, 0), (300, 100)]
    assert drawing.corner_points(branch)[0] == (300, 0)
    # A joint moves the same way
    drawing.connect_branch(wire, (0, (100, 0)), drawing.led("L3", 400, 300), clicks=[(100, 300)])
    joint_move = drawing.point_move((100, 0))
    assert joint_move is not None
    assert drawing.joint_bounds(joint_move.wire, joint_move.segment) == joint_move.bounds


def test_point_that_cannot_move():
    """A corner of a single wire, without a straight line through it, doesn't move"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led = drawing.led("L", 400, 100)
    drawing.connect_ports(a, led)
    assert drawing.point_move((390, 0)) is None
    assert drawing.point_move((1000, 1000)) is None


def test_merge_segments_at_a_joint():
    """Two segments in a straight line, with a joint between: the joint can be removed"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 300)
    drawing.connect_ports(a, led1)
    wire = (a, led1)
    path = list(drawing.path(wire))
    drawing.add_joint(wire, 0, (200, 0))
    # The segments on each side of the joint, and the joint itself
    assert [drawing.unused_joint(wire, segment) for segment in (0, 1, 2)] == [1, 1, 1]
    drawing.remove_joint(wire, 2)
    assert drawing.path(wire) == path
    # A joint where a wire starts stays
    drawing.connect_branch(wire, (0, (200, 0)), led2)
    assert drawing.unused_joint(wire, 0) is None
    with pytest.raises(ValueError, match="No joint"):
        drawing.remove_joint(wire, 0)


def test_merge_a_straight_wire():
    """
    A straight wire keeps one vertical segment, without length: merging moves it to the
    end of the wire, where it isn't a joint
    """
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led = drawing.led("L", 400, 0)
    drawing.connect_ports(a, led)
    wire = (a, led)
    drawing.set_path(wire, [200])
    assert drawing.unused_joint(wire, 0) == 1
    drawing.remove_joint(wire, 0)
    assert drawing.path(wire) == [400]
    assert drawing.unused_joint(wire, 0) is None
    # Several vertical segments, the last one without length
    drawing.set_path(wire, [100, 50, 200, 0, 300])
    assert drawing.unused_joint(wire, 4) == 5
    drawing.remove_joint(wire, 4)
    assert drawing.path(wire) == [100, 50, 200]


def test_move_a_point_at_the_end_of_a_port_segment():
    """
    A point that moves its wire's segment at a port: the segment is split next to the
    port, so that the wire still leaves the port straight
    """
    drawing = Drawing()
    a = drawing.button("A", 0, 100)
    led1 = drawing.led("L1", 400, 300)
    led2 = drawing.led("L2", 400, 0)
    drawing.connect_ports(a, led1, clicks=[(200, 300)])
    wire = (a, led1)
    assert drawing.corner_points(wire)[:3] == [(40, 100), (200, 100), (200, 300)]
    # Up from the corner where the wire turns down: a straight line up and down
    drawing.connect_branch(wire, 1, led2, clicks=[(200, 0)])
    move = drawing.point_move((200, 100))
    assert move is not None and move.split
    drawing.move_point(move, 150)
    points = drawing.corner_points(wire)
    assert points[:4] == [(40, 100), (50, 100), (50, 150), (200, 150)]
    assert drawing.corner_points((a, led2))[0] == (200, 150)


def pieces_of(drawing):
    """The drawn segments on each piece of the lines"""
    found = {}
    for key, run in drawing.runs().items():
        found.setdefault(run, set()).add(key)
    return found


def test_pieces_of_a_line(bus):
    """
    The pieces of a line are between its ports and where wires meet: B's wire ends where
    the branch to LED 2 starts, so A to there, on to LED 1, the branch, and B's wire
    """
    drawing, a, _b, led1, led2 = bus
    runs = drawing.runs()
    assert len(set(runs.values())) == 4
    # The first segment of A's wire, and the one from its port down to the joint
    assert runs[((a, led1), 0)] == runs[((a, led1), 1)]
    assert runs[((a, led1), 0)] != runs[((a, led2), 1)]


def test_delete_a_piece_at_the_output(bus):
    """Without the piece from A, A drives nothing, B still drives both LEDs"""
    drawing, a, _b, led1, led2 = bus
    before = shape(drawing)
    drawing.delete_runs([((a, led1), 0)])
    assert a.wired_ports == []
    assert drawing.drivers(led1) == drawing.drivers(led2) == ["B"]
    # The other pieces are where they were
    ((_, segments_after),) = shape(drawing)
    ((_, segments_before),) = before
    assert len(segments_after) < len(segments_before)
    for wire in drawing.connections():
        assert drawing.is_connected(wire)


def test_delete_a_piece_to_an_input(bus):
    """Without the piece to LED 2, LED 2 isn't driven, the rest of the line stays"""
    drawing, a, _b, led1, led2 = bus
    drawing.delete_runs([((a, led2), 1)])
    assert drawing.drivers(led2) == []
    assert drawing.drivers(led1) == ["A", "B"]


def test_delete_a_piece_in_the_middle():
    """A piece between two points: the line is two lines after"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 300)
    led2 = drawing.led("L2", 400, 100)
    led3 = drawing.led("L3", 400, 200)
    drawing.connect_ports(a, led1, clicks=[(200, 300)])
    wire = (a, led1)
    # The lower one first: segment 1 is from (200, 0) down to it then
    drawing.connect_branch(wire, (1, (200, 200)), led3)
    drawing.connect_branch(wire, (1, (200, 100)), led2)
    points = drawing.corner_points(wire)
    middle_piece = next(
        (wire, segment)
        for segment in range(len(points) - 1)
        if points[segment] != points[segment + 1]
        and on_segment(points[segment], points[segment + 1], (200, 150))
    )
    drawing.delete_runs([middle_piece])
    assert drawing.drivers(led2) == ["A"]
    assert drawing.drivers(led1) == drawing.drivers(led3) == []


def test_point_at_a_port_does_not_move():
    """A point where wires meet at a port: the port can't move"""
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, -100)
    b = drawing.button("B", -200, 0)
    drawing.connect_ports(a, led1)
    drawing.connect_ports(a, led2)
    # Into A's output port from the left: three ways at the port
    drawing.connect_ports(b, a)
    assert drawing.point_move((40, 0)) is None


def test_complete_a_line_of_a_file():
    """
    A file where B drives only L1 of the line that A draws to L1 and L2: once its wires
    are drawn, B drives L2 too, as the line does when it is saved and loaded again
    """
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    b = drawing.button("B", 0, 300)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 400, 200)
    a.wire = led1
    b.wire = led1
    a.wire = led2
    drawing.from_dict({})
    assert drawing.complete_lines() == [(b, led2)]
    assert drawing.drivers(led2) == ["A", "B"]
    assert drawing.is_implied((b, led2))
    assert drawing.complete_lines() == []
    round_trip(drawing)


def test_port_of_another_width_is_left_off_a_line():
    """
    A line of a file with a port that no longer has the width of the line (a Verilog
    module that was changed) connects and draws the other ports, not that one
    """
    drawing = Drawing()
    a = drawing.button("A", 0, 0)
    led = drawing.led("L", 400, 0)
    wide = drawing.add(StaticValue(drawing.circuit, "S", width=4), 0, 200).O
    line = LineDataClass(
        ports=["A.O", "L.I", "S.O"],
        points={"1": [200, 0], "2": [200, 200]},
        segments=[["A.O", "1"], ["1", "L.I"], ["1", "2"], ["2", "S.O"]],
    )
    errors = []
    line.connect(drawing.circuit, errors)
    assert len(errors) == 1 and "S.O" in errors[0]
    drawing.from_lines([line])
    assert drawing.drawn() == [(a, led)]
    assert wide.wired_ports == []
    assert drawing.to_lines()[0].ports == ["A.O", "L.I"]


def test_move_a_point_that_another_line_runs_through():
    """
    A wire of another line, drawn first, runs straight through the dot at a corner: the
    dot is of its own line, and moves as without the other wire
    """
    drawing = Drawing()
    p = drawing.button("P", 0, -100)
    q = drawing.led("Q", 400, 50)
    a = drawing.button("A", 0, 0)
    led1 = drawing.led("L1", 400, 100)
    led2 = drawing.led("L2", 600, 0)
    drawing.connect_ports(p, q)
    assert drawing.corner_points((p, q)) == [(40, -100), (390, -100), (390, 50), (400, 50)]
    drawing.connect_ports(a, led1)
    drawing.connect_branch((a, led1), 1, led2)
    assert drawing.drawn()[0] == (p, q)
    move = drawing.point_move((390, 0))
    assert move is not None
    assert move.wire == (a, led1) and move.segment == 1


# --------------------------------------------------------------------------------------
# Inout ports, both outputs and inputs of their line
# --------------------------------------------------------------------------------------


@pytest.fixture(name="inout_bus")
def fixture_inout_bus():
    """
    Two inout ports on a line, with a branch to an LED, and a button that joins the line
    """
    drawing = Drawing()
    a = drawing.transceiver("A", 0, 0)
    b = drawing.transceiver("B", 0, 300)
    led = drawing.led("L", 400, 100)
    button = drawing.button("P", 0, 500)
    drawing.connect_ports(a, b)
    drawing.connect_branch((a, b), middle(drawing, (a, b), 0), led)
    drawing.connect_join(button, (a, b), middle(drawing, (a, b), 1))
    return drawing, a, b, led, button


def test_inout_ports_drive_each_other():
    """A wire between two inout ports connects them both ways, one way is implied"""
    drawing = Drawing()
    a = drawing.transceiver("A", 0, 0)
    b = drawing.transceiver("B", 0, 300)
    drawing.connect_ports(a, b)
    assert drawing.drivers(a) == ["B"]
    assert drawing.drivers(b) == ["A"]
    assert drawing.keys() == (["B.IO"], ["A.IO"])
    line = drawing.line(("port", a))
    assert line.outputs == [a, b]
    assert line.inputs == [a, b]


def test_inout_line(inout_bus):
    """Every output of the line drives every input, the inout ports are both"""
    drawing, a, b, led, _ = inout_bus
    assert drawing.drivers(a) == ["B", "P"]
    assert drawing.drivers(b) == ["A", "P"]
    assert drawing.drivers(led) == ["A", "B", "P"]
    assert drawing.complete_lines() == []
    round_trip(drawing)


def test_inout_line_values():
    """The inout ports read what the others drive on the line, and so does the LED"""
    drawing = Drawing()
    a = drawing.transceiver("A", 0, 0)
    b = drawing.transceiver("B", 0, 300)
    led = drawing.led("L", 400, 100)
    drawing.connect_ports(a, b)
    drawing.connect_branch((a, b), middle(drawing, (a, b), 0), led)
    drawing.circuit.init()
    for drive_a, drive_b, expected in [("Z", "Z", "Z"), (1, "Z", 1), (1, 0, "X"), ("Z", 0, 0)]:
        a.parent().drive(drive_a)
        b.parent().drive(drive_b)
        drawing.circuit.run(ns=10)
        assert (a.read_value(), b.read_value(), led.value) == (expected,) * 3
        assert drawing.line_value((a, b)) == expected


def test_delete_the_wire_between_inout_ports():
    """Both ways are disconnected"""
    drawing = Drawing()
    a = drawing.transceiver("A", 0, 0)
    b = drawing.transceiver("B", 0, 300)
    drawing.connect_ports(a, b)
    drawing.delete_wires([(a, b)])
    assert drawing.drivers(a) == drawing.drivers(b) == []
    assert drawing.drawn() == []


def test_delete_an_inout_port_of_the_line(inout_bus):
    """The other ports of the line stay connected, the inout port that is left both ways"""
    drawing, a, b, led, _ = inout_bus
    drawing.remove_component(b.parent())
    drawing.circuit.delete_component(b.parent())
    assert drawing.drivers(a) == ["P"]
    assert drawing.drivers(led) == ["A", "P"]
    assert drawing.keys() == (["A.IO", "L.I<A.IO"], ["L.I<P.O"])


def test_connect_a_line_of_inout_ports(inout_bus):
    """A line of a circuit file connects the inout ports both ways, not to themselves"""
    drawing, a, b, led, button = inout_bus
    (line,) = [line for line in drawing.to_lines() if "A.IO" in line.ports]
    for port in (a, b, button):
        port.remove_wires()
    errors = []
    line.connect(drawing.circuit, errors)
    assert errors == []
    assert drawing.drivers(a) == ["B", "P"]
    assert drawing.drivers(b) == ["A", "P"]
    assert drawing.drivers(led) == ["A", "B", "P"]


class RotatedDrawing(Drawing):
    """A drawing where some components are rotated a quarter, clockwise"""

    def __init__(self):
        super().__init__()
        self.turned = set()

    def port_pos(self, port):
        if port.parent() not in self.turned:
            return super().port_pos(port)
        # The outputs below the middle of the component, the inputs above it
        x, y = self.places[port.parent()]
        return (x + 20, y + 20) if port.is_output() else (x + 20, y - 20)

    def port_direction(self, port):
        direction = super().port_direction(port)
        return rotated(direction, 90) if port.parent() in self.turned else direction


def test_drawing_with_a_rotated_component():
    drawing = RotatedDrawing()
    button = drawing.button("B", 0, 0)
    led = drawing.led("L", 200, 100)
    other = drawing.led("M", 200, 300)
    drawing.turned.add(led.parent())
    drawing.connect_ports(button, led)
    # Into the LED's input from above, it faces up
    points = _route_points(
        drawing.port_pos(button), drawing.port_pos(led), drawing.path((button, led))
    )
    assert points[-2][0] == points[-1][0] == 220
    assert points[-2][1] < points[-1][1]
    # A wire between ports that aren't rotated has the path it always had
    drawing.connect_ports(button, other)
    assert drawing.path((button, other)) == [190]


def _route_points(start, end, path):
    """The corners of a wire, without the segments without length"""
    points = []
    for point in corner_points(start, end, path):
        if not points or point != points[-1]:
            points.append(point)
    return points
