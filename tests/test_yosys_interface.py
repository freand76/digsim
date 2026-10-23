# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test the ports of a Yosys component that change with its Verilog, and their wires"""

import json
import tempfile
from pathlib import Path

import platformdirs
import pytest

from digsim.app._line_graph import without_ports
from digsim.app._wire_lines import WireDrawing
from digsim.app._yosys_interface import (
    InterfaceChanges,
    change_message,
    components_of_file,
    interface_changes,
    load_netlists,
    removed_wires,
)
from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton, StaticValue, YosysComponent
from digsim.circuit.components._yosys_component import YosysComponentException
from digsim.storage_model import LineDataClass
from digsim.synth import SynthesisException
from digsim.utils import YosysNetlist


BEFORE = """
module m(input a, input [3:0] b, output y, output [3:0] q);
   assign y = a;
   assign q = b;
endmodule
"""
# y is gone, b is wider, z is new
AFTER = """
module m(input a, input [7:0] b, output z, output [3:0] q);
   assign z = a;
   assign q = b[3:0];
endmodule
"""


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


@pytest.fixture(name="verilog")
def fixture_verilog(work_dir):
    path = work_dir / "m.v"
    path.write_text(BEFORE, encoding="utf-8")
    return path


def test_interface_changes():
    old = {"a": (False, 1), "b": (False, 4), "y": (True, 1), "q": (True, 4)}
    new = {"a": (True, 1), "b": (False, 8), "z": (True, 1), "q": (True, 4)}
    changes = interface_changes(old, new)
    assert changes == InterfaceChanges(
        added=["z"], removed=["y"], width={"b": (4, 8)}, direction=["a"]
    )
    assert changes
    assert changes.gone() == {"a", "b", "y"}
    assert changes.describe() == [
        "Port 'y' is removed",
        "Port 'b' has 8 bits instead of 4",
        "Port 'a' changes direction",
        "Port 'z' is new",
    ]
    assert not interface_changes(old, dict(old))


def test_only_added_ports_remove_no_wires():
    changes = interface_changes({"a": (False, 1)}, {"a": (False, 1), "b": (False, 1)})
    assert changes
    assert changes.gone() == set()


def test_removed_wires():
    lines = [
        LineDataClass(ports=["A.O", "m.a", "m.b"]),
        LineDataClass(ports=["m.y", "L.I"]),
        LineDataClass(ports=["other.y", "L2.I"]),
    ]
    changes = InterfaceChanges(removed=["y"], width={"b": (4, 8)})
    assert removed_wires(lines, ["m"], changes) == ["m.b", "m.y"]


def test_change_message():
    changes = InterfaceChanges(removed=["y"])
    text = change_message("m", changes, ["m.y"])
    assert "The ports of 'm' change" in text
    assert " - Port 'y' is removed" in text
    assert " - m.y" in text
    assert "can't be undone" in text
    assert "wires" not in change_message("m", InterfaceChanges(added=["z"]), [])


def test_component_interface(verilog):
    circuit = Circuit()
    component = YosysComponent(circuit, verilog)
    assert component.source_file == str(verilog)
    assert not component.functional
    assert component.interface() == {
        "a": (False, 1),
        "b": (False, 4),
        "y": (True, 1),
        "q": (True, 4),
    }
    netlist = YosysNetlist(**YosysComponent.synthesize_file(verilog))
    assert YosysComponent.netlist_interface(netlist) == component.interface()


def test_components_of_file(verilog, work_dir, monkeypatch):
    circuit = Circuit()
    first = YosysComponent(circuit, verilog)
    monkeypatch.chdir(work_dir)
    second = YosysComponent(circuit, "m.v", functional=True)
    other_path = work_dir / "other.v"
    other_path.write_text(BEFORE.replace("module m", "module other"), encoding="utf-8")
    YosysComponent(circuit, other_path)
    Led(circuit, "L")
    assert components_of_file(circuit, verilog) == [first, second]
    assert components_of_file(circuit, work_dir / "missing.v") == []


def test_load_netlists(verilog):
    netlists = load_netlists(verilog, {False, True})
    assert set(netlists) == {False, True}
    assert netlists[False] == YosysComponent.synthesize_file(verilog)
    assert netlists[True] == YosysComponent.synthesize_file(verilog, functional=True)
    log = []
    assert set(load_netlists(verilog, {True}, log=log, cached=False)) == {True}
    assert len(log) > 0


def test_load_netlists_of_a_netlist_file(verilog, work_dir):
    path = work_dir / "m.json"
    path.write_text(json.dumps(YosysComponent.synthesize_file(verilog)), encoding="utf-8")
    netlists = load_netlists(path, {False, True})
    assert netlists[False] == netlists[True] == YosysComponent.synthesize_file(verilog)
    path.write_text('{"not": "a netlist"}', encoding="utf-8")
    with pytest.raises(YosysComponentException):
        load_netlists(path, {False})


def test_load_netlists_errors(verilog, work_dir):
    verilog.write_text("module m(input a; endmodule\n", encoding="utf-8")
    with pytest.raises(SynthesisException):
        load_netlists(verilog, {False})
    with pytest.raises(OSError):
        load_netlists(work_dir / "missing.v", {False})


class Drawing(WireDrawing):
    """The wires of a circuit, each component at its place, its ports below each other"""

    def __init__(self, circuit, places):
        super().__init__()
        self.circuit = circuit
        self.places = places

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
        x, y = self.places[port.parent().name()]
        component = port.parent()
        side = component.outports() if port.is_output() else component.inports()
        y += 20 * side.index(port)
        return (x + 40, y) if port.is_output() else (x, y)

    def port_rect(self, port):
        x, y = self.port_pos(port)
        return x - 5, y - 5, 10, 10


PLACES = {"A": (0, 0), "S": (0, 100), "m": (200, 0), "L1": (400, 0), "L2": (400, 100)}


def _circuit(verilog):
    circuit = Circuit()
    PushButton(circuit, "A")
    StaticValue(circuit, "S", width=4)
    YosysComponent(circuit, verilog)
    Led(circuit, "L1")
    Led(circuit, "L2")
    return circuit


def test_changed_ports_lose_their_wires(verilog):
    """
    The circuit is built again from the new Verilog and the lines without the ports
    that are gone, as the GUI does when the ports change
    """
    circuit = _circuit(verilog)
    drawing = Drawing(circuit, PLACES)
    a, s, m = (circuit.get_component(name) for name in ("A", "S", "m"))
    led1, led2 = circuit.get_component("L1"), circuit.get_component("L2")
    drawing.connect_ports(a.O, m.a)
    drawing.connect_ports(s.O, m.b)
    drawing.connect_ports(m.y, led1.I)
    points = drawing.corner_points((m.y, led1.I))
    drawing.connect_branch((m.y, led1.I), (1, points[1]), led2.I)
    lines = drawing.to_lines()

    verilog.write_text(AFTER, encoding="utf-8")
    netlist = YosysNetlist(**load_netlists(verilog, {False})[False])
    changes = interface_changes(m.interface(), YosysComponent.netlist_interface(netlist))
    assert changes.gone() == {"b", "y"}
    assert removed_wires(lines, ["m"], changes) == ["m.b", "m.y"]
    lines = without_ports(lines, {f"m.{port}" for port in changes.gone()})

    circuit = _circuit(verilog)
    errors = []
    for line in lines:
        line.connect(circuit, errors)
    assert errors == []
    drawing = Drawing(circuit, PLACES)
    drawing.from_lines(lines)
    a, m = circuit.get_component("A"), circuit.get_component("m")
    led1, led2 = circuit.get_component("L1"), circuit.get_component("L2")
    assert m.interface()["b"] == (False, 8)
    # The wire to a is kept, the one to b is gone, and the LEDs keep the wire between them
    assert drawing.connections() == [(a.O, m.a)]
    assert sorted(drawing.drawn(), key=str) == sorted([(a.O, m.a), (led1.I, led2.I)], key=str)
    for saved in drawing.to_lines():
        nodes = {node for segment in saved.segments for node in segment}
        assert nodes <= set(saved.ports) | set(saved.points)
        assert "m.y" not in saved.ports and "m.b" not in saved.ports


def test_given_netlists(verilog, work_dir):
    """Components built with given netlists don't read their files, in order"""
    circuit = Circuit()
    first = YosysComponent(circuit, verilog)
    netlist = first.netlist()
    assert YosysComponent.netlist_interface(netlist) == first.interface()
    verilog.write_text("module m(input a; endmodule\n", encoding="utf-8")
    after = YosysNetlist(**YosysComponent.synthesize_file(_after_file(work_dir)))
    with YosysComponent.given_netlists([(verilog, False, netlist), (str(verilog), False, after)]):
        second = YosysComponent(circuit, verilog)
        third = YosysComponent(circuit, verilog)
        # None left: the file is read, it has an error now
        with pytest.raises(SynthesisException):
            YosysComponent(circuit, verilog)
        # Another variant reads its file too
        with pytest.raises(SynthesisException):
            YosysComponent(circuit, verilog, functional=True)
    assert second.interface() == first.interface()
    assert set(third.interface()) == {"a", "b", "z", "q"}
    with pytest.raises(SynthesisException):
        YosysComponent(circuit, verilog)


def _after_file(work_dir):
    path = work_dir / "after.v"
    path.write_text(AFTER, encoding="utf-8")
    return path
