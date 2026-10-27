# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the component catalog of the GUI and its search"""

import pytest

import digsim.circuit.components
from digsim.app._component_catalog import CATALOG, COMPONENT_GROUPS, search_components
from digsim.circuit.components.atoms import Component


def test_catalog_has_components():
    """Each entry is a component class, once"""
    names = [entry.name for _, entries in COMPONENT_GROUPS for entry in entries]
    assert len(names) == len(set(names)) == len(CATALOG)
    for name in names:
        assert issubclass(getattr(digsim.circuit.components, name), Component)


@pytest.mark.parametrize(
    ("query", "first"),
    [
        ("led", "Led"),
        ("LED bar", "LedBar"),
        ("and", "AND"),
        ("flp", "FlipFlop"),
        ("7seg", "SevenSegment"),
        ("mem", "RAM"),
        ("rom", "ROM"),
        ("prb", "Probe"),
        ("tristate", "TristateBuffer"),
        ("splitter", "Bus2Wires"),
        ("verilog", "YosysComponent"),
        ("74", "IntegratedCircuit"),
        ("wire sink", "LabelWireIn"),
        ("anlz", "LogicAnalyzer"),
    ],
)
def test_search_components(query, first):
    """The best match comes first, also with skipped letters and by a keyword"""
    assert search_components(query)[0].name == first


def test_search_components_without_match():
    """An empty query, or one that matches nothing, finds nothing"""
    assert search_components("") == []
    assert search_components("   ") == []
    assert search_components("zzz") == []
