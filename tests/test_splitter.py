# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the splitter, a bus split into groups of bits"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Probe, Splitter, StaticValue, TristateBuffer
from digsim.circuit.components._splitter import group_text, parse_groups
from digsim.circuit.components.atoms import ComponentException


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


def _run(circuit):
    circuit.init()
    circuit.run(ns=100)


def test_split():
    circuit = Circuit()
    splitter = Splitter(circuit, groups=[4, 1, 3])
    assert [port.name() for port in splitter.groups] == ["bus_3_0", "bus_4", "bus_7_5"]
    assert [port.width for port in splitter.groups] == [4, 1, 3]
    assert splitter.bus.width == 8
    source = StaticValue(circuit, width=8, value=0xB5)
    source.O.wire = splitter.bus
    probes = [Probe(circuit, width=port.width) for port in splitter.groups]
    for port, probe in zip(splitter.groups, probes):
        port.wire = probe.I
    _run(circuit)
    assert [probe.I.value for probe in probes] == [0x5, 1, 0x5]


def test_merge():
    circuit = Circuit()
    splitter = Splitter(circuit, groups=[4, 4], direction="merge")
    assert splitter.bus.is_output()
    assert all(port.is_input() for port in splitter.groups)
    for port, value in zip(splitter.groups, (0xA, 0x3)):
        StaticValue(circuit, width=4, value=value).O.wire = port
    probe = Probe(circuit, width=8)
    splitter.bus.wire = probe.I
    _run(circuit)
    assert probe.I.value == 0x3A


def test_split_then_merge_back():
    """Groups wired back into a merging splitter give the bus again"""
    circuit = Circuit()
    split = Splitter(circuit, groups=[3, 5])
    merge = Splitter(circuit, groups=[3, 5], direction="merge")
    for out_port, in_port in zip(split.groups, merge.groups):
        out_port.wire = in_port
    source = StaticValue(circuit, width=8, value=0xC7)
    source.O.wire = split.bus
    probe = Probe(circuit, width=8)
    merge.bus.wire = probe.I
    _run(circuit)
    assert probe.I.value == 0xC7


def test_undefined_and_not_driven():
    """A group that is "X" makes the bus "X", "Z" groups make it "Z" if all are"""
    circuit = Circuit()
    merge = Splitter(circuit, groups=[2, 2], direction="merge")
    low = TristateBuffer(circuit, width=2)
    high = TristateBuffer(circuit, width=2)
    low.Y.wire = merge.bus_1_0
    high.Y.wire = merge.bus_3_2
    enables = []
    for buffer in (low, high):
        StaticValue(circuit, width=2, value=1).O.wire = buffer.A
        enable = StaticValue(circuit, value=0)
        enable.O.wire = buffer.OE
        enables.append(enable)
    probe = Probe(circuit, width=4)
    merge.bus.wire = probe.I
    _run(circuit)
    assert probe.I.value == "Z"
    enables[0].parameter_set("value", 1)
    enables[0].reconfigure()
    circuit.run(ns=100)
    assert probe.I.value == "X"
    enables[1].parameter_set("value", 1)
    enables[1].reconfigure()
    circuit.run(ns=100)
    assert probe.I.value == 0x5


def test_save_and_load(tmp_path):
    circuit = Circuit(name="main")
    Splitter(circuit, groups=[2, 6], direction="merge")
    circuit.to_json_file(tmp_path / "main.circuit")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "main.circuit")
    splitter = loaded.get_component("Splitter")
    assert [port.name() for port in splitter.groups] == ["bus_1_0", "bus_7_2"]
    assert splitter.is_merge()


@pytest.mark.parametrize(
    ("text", "groups"), [("4, 4", [4, 4]), ("1 3 4", [1, 3, 4]), (" 16,16 ", [16, 16])]
)
def test_parse_groups(text, groups):
    assert parse_groups(text) == groups
    assert parse_groups(group_text(groups)) == groups


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("8", "at least two"),
        ("4, x", "widths"),
        ("4, 0", "at least one bit"),
        ("16, 16, 1", "at most 32"),
    ],
)
def test_bad_groups(text, message):
    with pytest.raises(ComponentException, match=message):
        parse_groups(text)


def test_bad_direction():
    with pytest.raises(ComponentException, match="split or merge"):
        Splitter(Circuit(), direction="up")
