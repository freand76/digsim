# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""The search of the netlist view"""

from digsim.app._netlist_search import entry_text, search_entries
from digsim.utils import NetlistEntry


ENTRIES = [
    NetlistEntry("signal", "regfile", frozenset({"a", "b"}), 512),
    NetlistEntry("signal", "rd_field", frozenset({"c"}), 5),
    NetlistEntry("signal", "pc_word", frozenset({"d"}), 30),
    NetlistEntry("type", "DFFE_PP0P", frozenset({"a", "b", "d"})),
    NetlistEntry("line", "rv32e.v:120", frozenset({"c"})),
]


def test_an_empty_search_lists_everything():
    assert search_entries("", ENTRIES) == ENTRIES


def test_the_best_match_comes_first():
    assert search_entries("regfile", ENTRIES)[0].name == "regfile"
    assert search_entries("rd", ENTRIES)[0].name == "rd_field"
    # With skipped letters
    assert search_entries("rgfl", ENTRIES)[0].name == "regfile"


def test_a_kind_finds_its_entries():
    assert [entry.name for entry in search_entries("cell type", ENTRIES)] == ["DFFE_PP0P"]
    assert [entry.name for entry in search_entries("source line", ENTRIES)] == ["rv32e.v:120"]


def test_the_text_of_an_entry():
    assert entry_text(ENTRIES[0]) == "regfile  (signal, 512 bits, 2 cells)"
    assert entry_text(ENTRIES[2]) == "pc_word  (signal, 30 bits, 1 cell)"
