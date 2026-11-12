# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the fuzzy search of the IC selector"""

import pytest

from digsim.app._ic_search import search_ics
from digsim.circuit.components import IntegratedCircuit


ICS = {
    "4017": "Decade counter with 10 decoded outputs",
    "7448": "BCD to 7-segment decoder",
    "74138": "3-to-8 line decoder, demultiplexer (demux)",
    "74162": "Synchronous decade counter with parallel load",
    "74181": "4-bit arithmetic logic unit (ALU)",
    "74194": "4-bit bidirectional universal shift register",
    "74595": "8-bit shift register with output register",
}


@pytest.mark.parametrize(
    "query, expected",
    [
        # All ICs, in number order
        ("", ["4017", "7448", "74138", "74162", "74181", "74194", "74595"]),
        # The beginning of a number
        ("7419", ["74194"]),
        # A word of the description, and the beginning of one
        ("counter", ["4017", "74162"]),
        ("shift", ["74194", "74595"]),
        ("alu", ["74181"]),
        # Skipped letters
        ("shft", ["74194", "74595"]),
        # Every word must match, in any case
        ("DECADE load", ["74162"]),
        ("xyz", []),
    ],
)
def test_search_ics(query, expected):
    assert search_ics(query, ICS) == expected


def test_best_match_first():
    """A number that starts with the query comes before one that only contains it"""
    assert search_ics("41", {"7441": "", "4130": ""}) == ["4130", "7441"]


def test_bundled_ics_have_descriptions():
    """Every bundled IC has a description to search for"""
    ics = IntegratedCircuit.available()
    assert len(ics) >= 13
    assert all(ics.values()), [name for name, description in ics.items() if not description]
