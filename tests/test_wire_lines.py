# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the lines of the wires drawn in the GUI, with every wire on them"""

import pytest

from digsim.app._wire_key import drawn_key, wire_key
from digsim.app._wire_lines import WireDrawing
from digsim.circuit import Circuit
from digsim.circuit.components import (
    Led,
    OnOffSwitch,
    PortConnectionError,
    PushButton,
    StaticValue,
)
from digsim.storage_model import GuiWireDataClass


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
