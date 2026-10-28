# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test subcircuits, circuit files used as components"""

import json

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import (
    AND,
    OR,
    XOR,
    CircuitInOut,
    CircuitInput,
    CircuitOutput,
    Probe,
    StaticValue,
    SubCircuit,
    SubCircuitException,
    TristateBuffer,
)


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


def _half_adder(path):
    """A half adder circuit file: s = a ^ b, c = a & b"""
    circuit = Circuit(name="half_adder")
    a = CircuitInput(circuit, label="a")
    b = CircuitInput(circuit, label="b")
    s = CircuitOutput(circuit, label="s")
    c = CircuitOutput(circuit, label="c")
    xor = XOR(circuit)
    and_gate = AND(circuit)
    for gate in (xor, and_gate):
        a.port("a").wire = gate.A
        b.port("b").wire = gate.B
    xor.Y.wire = s.port("s")
    and_gate.Y.wire = c.port("c")
    circuit.to_json_file(path)
    return path


def _drive(circuit, port, value):
    source = StaticValue(circuit, width=port.width, value=value)
    source.O.wire = port
    return source


def _run(circuit):
    circuit.init()
    circuit.run(ns=100)


@pytest.mark.parametrize(("a", "b"), [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_half_adder(tmp_path, a, b):
    """The ports are the circuit ports of the file, the parts work like in the file"""
    path = _half_adder(tmp_path / "half_adder.circuit")
    circuit = Circuit()
    adder = SubCircuit(circuit, path)
    assert adder.name() == "half_adder"
    assert adder.interface() == {
        "a": ("in", 1),
        "b": ("in", 1),
        "c": ("out", 1),
        "s": ("out", 1),
    }
    _drive(circuit, adder.a, a)
    _drive(circuit, adder.b, b)
    _run(circuit)
    assert (adder.s.value, adder.c.value) == ((a + b) & 1, (a + b) >> 1)


def test_parts_are_named_under_the_subcircuit(tmp_path):
    path = _half_adder(tmp_path / "half_adder.circuit")
    circuit = Circuit()
    adder = SubCircuit(circuit, path)
    paths = sorted(
        component.path()
        for component in circuit.components
        if not component.is_toplevel() and component.parent is adder
    )
    assert paths == ["half_adder.AND", "half_adder.XOR"]
    # Not saved: only the subcircuit is a component of the circuit
    assert circuit.get_toplevel_components() == [adder]


def _full_adder(folder):
    """A full adder from two half adders in subfolders, the paths relative to the file"""
    (folder / "parts").mkdir()
    half = _half_adder(folder / "parts" / "half_adder.circuit")
    circuit = Circuit(name="full_adder")
    a = CircuitInput(circuit, label="a")
    b = CircuitInput(circuit, label="b")
    cin = CircuitInput(circuit, label="cin")
    s = CircuitOutput(circuit, label="s")
    cout = CircuitOutput(circuit, label="cout")
    first = SubCircuit(circuit, half)
    second = SubCircuit(circuit, half)
    or_gate = OR(circuit)
    a.port("a").wire = first.a
    b.port("b").wire = first.b
    first.s.wire = second.a
    cin.port("cin").wire = second.b
    second.s.wire = s.port("s")
    first.c.wire = or_gate.A
    second.c.wire = or_gate.B
    or_gate.Y.wire = cout.port("cout")
    path = folder / "full_adder.circuit"
    circuit.to_json_file(path)
    return path


def test_nested_subcircuits(tmp_path):
    """A subcircuit of subcircuits, their files relative to its file"""
    path = _full_adder(tmp_path)
    stored = json.loads(path.read_text())["circuit"]["components"]
    assert {c["settings"].get("path") for c in stored if "SubCircuit" in c["type"]} == {
        "parts/half_adder.circuit"
    }
    for a in (0, 1):
        for b in (0, 1):
            for cin in (0, 1):
                circuit = Circuit()
                adder = SubCircuit(circuit, path)
                _drive(circuit, adder.a, a)
                _drive(circuit, adder.b, b)
                _drive(circuit, adder.cin, cin)
                _run(circuit)
                total = a + b + cin
                assert (adder.s.value, adder.cout.value) == (total & 1, total >> 1)


def _bus_driver(path):
    """A circuit that drives 'data' on the inout 'bus' while 'en' is 1"""
    circuit = Circuit(name="bus_driver")
    data = CircuitInput(circuit, label="data", width=4)
    enable = CircuitInput(circuit, label="en")
    bus = CircuitInOut(circuit, label="bus", width=4)
    heard = CircuitOutput(circuit, label="heard", width=4)
    buffer = TristateBuffer(circuit, width=4)
    data.port("data").wire = buffer.A
    enable.port("en").wire = buffer.OE
    buffer.Y.wire = bus.port("bus")
    bus.port("bus").wire = heard.port("heard")
    circuit.to_json_file(path)
    return path


def test_inout_ports_share_a_bus(tmp_path):
    """Two subcircuits on one bus: the one that is enabled drives it, both hear it"""
    path = _bus_driver(tmp_path / "bus_driver.circuit")
    circuit = Circuit()
    first = SubCircuit(circuit, path, name="first")
    second = SubCircuit(circuit, path, name="second")
    assert first.bus.is_inout()
    first.bus.wire = second.bus
    second.bus.wire = first.bus
    probe = Probe(circuit, width=4)
    first.bus.wire = probe.I
    _drive(circuit, first.data, 5)
    _drive(circuit, second.data, 9)
    first_enable = _drive(circuit, first.en, 1)
    _drive(circuit, second.en, 0)
    _run(circuit)
    assert (probe.I.value, first.heard.value, second.heard.value) == (5, 5, 5)
    first_enable.parameter_set("value", 0)
    first_enable.reconfigure()
    circuit.run(ns=100)
    assert probe.I.value == "Z"


def _gui_file(path, ports):
    """A GUI circuit file with circuit ports at positions, and nothing else"""
    components = [
        {
            "name": name,
            "type": f"digsim.circuit.components.{kind}",
            "settings": {"label": name, "width": 1},
        }
        for name, kind, _ in ports
    ]
    gui = {name: {"x": 100, "y": y, "z": 0} for name, _, y in ports}
    path.write_text(json.dumps({"circuit": {"name": "c", "components": components}, "gui": gui}))
    return path


def test_ports_in_order_from_top_to_bottom(tmp_path):
    path = _gui_file(
        tmp_path / "ports.circuit",
        [
            ("low", "CircuitInput", 300),
            ("high", "CircuitInput", 100),
            ("out", "CircuitOutput", 200),
        ],
    )
    circuit = Circuit()
    sub = SubCircuit(circuit, path)
    assert [port.name() for port in sub.ports] == ["high", "out", "low"]


def test_a_file_that_uses_itself(tmp_path):
    path = tmp_path / "loop.circuit"
    path.write_text(
        json.dumps(
            {
                "circuit": {
                    "name": "loop",
                    "components": [
                        {
                            "name": "loop",
                            "type": "digsim.circuit.components.SubCircuit",
                            "settings": {"path": "loop.circuit"},
                        }
                    ],
                }
            }
        )
    )
    with pytest.raises(SubCircuitException, match="uses itself: loop.circuit -> loop.circuit"):
        SubCircuit(Circuit(), path)


def test_a_missing_file(tmp_path):
    with pytest.raises(SubCircuitException, match="Could not read"):
        SubCircuit(Circuit(), tmp_path / "missing.circuit")


def test_reload(tmp_path):
    """Reload builds the parts again from the changed file, with the same ports"""
    path = _half_adder(tmp_path / "half_adder.circuit")
    circuit = Circuit()
    adder = SubCircuit(circuit, path)
    _drive(circuit, adder.a, 1)
    _drive(circuit, adder.b, 1)
    _run(circuit)
    assert adder.c.value == 1
    # The carry is an OR now
    data = json.loads(path.read_text())
    for component in data["circuit"]["components"]:
        if component["type"].endswith(".AND"):
            component["type"] = "digsim.circuit.components.OR"
    path.write_text(json.dumps(data))
    adder.reload()
    _run(circuit)
    assert (adder.s.value, adder.c.value) == (0, 1)
    # Other ports can't be reloaded like that
    data["circuit"]["components"] = [
        c for c in data["circuit"]["components"] if c["settings"].get("label") != "c"
    ]
    data["circuit"]["wires"] = [w for w in data["circuit"]["wires"] if not w["dst"].endswith(".c")]
    path.write_text(json.dumps(data))
    with pytest.raises(SubCircuitException, match="ports .* changed"):
        adder.reload()


def test_reload_with_moved_and_renamed_ports(tmp_path):
    """
    Ports in another order in the file, or other components, are the same ports: the
    subcircuit is reloaded, its ports keep their order
    """
    path = _half_adder(tmp_path / "half_adder.circuit")
    circuit = Circuit()
    adder = SubCircuit(circuit, path)
    order = [port.label for port in adder.file_ports()]
    data = json.loads(path.read_text())
    # The input a is another component, and b is above it
    text = (
        json.dumps(data)
        .replace('"CircuitInput"', '"input_a"')
        .replace('"CircuitInput.', '"input_a.')
    )
    data = json.loads(text)
    data["gui"] = {"CircuitInput_1": {"x": 0, "y": 0}, "input_a": {"x": 0, "y": 100}}
    path.write_text(json.dumps(data))
    adder.reload()
    assert [port.label for port in adder.file_ports()] == order
    _drive(circuit, adder.a, 1)
    _drive(circuit, adder.b, 0)
    _run(circuit)
    assert (adder.s.value, adder.c.value) == (1, 0)


def test_save_and_load_a_circuit_with_a_subcircuit(tmp_path):
    path = _half_adder(tmp_path / "half_adder.circuit")
    circuit = Circuit(name="main")
    adder = SubCircuit(circuit, path)
    _drive(circuit, adder.a, 1)
    _drive(circuit, adder.b, 0)
    circuit.to_json_file(tmp_path / "main.circuit")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "main.circuit")
    _run(loaded)
    assert loaded.get_component("half_adder").s.value == 1


def test_a_gui_file_with_lines(tmp_path):
    """The lines of a GUI file connect the parts, each output drives each input"""
    path = tmp_path / "xor.circuit"

    def component(name, kind, **settings):
        return {"name": name, "type": f"digsim.circuit.components.{kind}", "settings": settings}

    path.write_text(
        json.dumps(
            {
                "circuit": {
                    "name": "xor",
                    "components": [
                        component("a", "CircuitInput", label="a", width=1),
                        component("b", "CircuitInput", label="b", width=1),
                        component("XOR", "XOR", ports=2),
                        component("s", "CircuitOutput", label="s", width=1),
                        component("t", "CircuitOutput", label="t", width=1),
                    ],
                },
                "lines": [
                    {"ports": ["a.a", "XOR.A"]},
                    {"ports": ["b.b", "XOR.B"]},
                    # One output to two circuit outputs
                    {"ports": ["XOR.Y", "s.s", "t.t"]},
                ],
            }
        )
    )
    circuit = Circuit()
    sub = SubCircuit(circuit, path)
    _drive(circuit, sub.a, 1)
    _drive(circuit, sub.b, 0)
    _run(circuit)
    assert (sub.s.value, sub.t.value) == (1, 1)


def test_files_used(tmp_path):
    """The files a subcircuit file uses, also through its subcircuits"""
    from digsim.circuit.components._subcircuit import files_used

    path = _full_adder(tmp_path)
    assert files_used(path) == {(tmp_path / "parts" / "half_adder.circuit").resolve()}
    assert files_used(tmp_path / "parts" / "half_adder.circuit") == set()


@pytest.mark.parametrize(("a", "b"), [(5, 6), (15, 1), (9, 9), (0, 0)])
def test_example_4_bit_adder(a, b):
    """The 4-bit adder example: four full adders, each from two half adders"""
    from pathlib import Path

    from digsim.circuit.components import DipSwitch

    path = Path(__file__).parent.parent / "circuits" / "subcircuits" / "adder_4bit.circuit"
    circuit = Circuit()
    circuit.from_json_file(path)
    circuit.init()
    for name, value in (("DipSwitch", a), ("DipSwitch_1", b)):
        switch = circuit.get_component(name)
        assert isinstance(switch, DipSwitch)
        for bit in range(4):
            if value >> bit & 1:
                switch.select(bit)
                switch.onpress()
    circuit.run(ns=1000)
    total = a + b
    assert circuit.get_component("HexDigit").val.value == total & 15
    assert circuit.get_component("Led").I.value == total >> 4


def test_example_loaded_by_a_relative_path(monkeypatch):
    """The files of nested subcircuits are relative to each file, not to the circuit's"""
    from pathlib import Path

    monkeypatch.chdir(Path(__file__).parent.parent)
    circuit = Circuit()
    circuit.from_json_file("circuits/subcircuits/adder_4bit.circuit")
    assert len([c for c in circuit.get_toplevel_components() if isinstance(c, SubCircuit)]) == 4
