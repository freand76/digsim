# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The components that can be added in the GUI, by group, and the search of them (kept free
from Qt imports so that it can be tested without a display)
"""

from __future__ import annotations

from typing import NamedTuple

from digsim.app._ic_search import fuzzy_search


class CatalogEntry(NamedTuple):
    """A component that can be added: its class, the name shown, and words to find it by"""

    name: str
    display_name: str
    keywords: str = ""


COMPONENT_GROUPS: list[tuple[str, list[CatalogEntry]]] = [
    (
        "Input",
        [
            CatalogEntry("PushButton", "PushButton", "push button key momentary"),
            CatalogEntry("OnOffSwitch", "OnOffSwitch", "on off switch toggle"),
            CatalogEntry("DipSwitch", "DIP switch", "switches bits"),
            CatalogEntry("Clock", "Clock", "clock oscillator frequency square wave"),
            CatalogEntry("StaticValue", "StaticValue", "static value constant"),
        ],
    ),
    (
        "Output",
        [
            CatalogEntry("Led", "Led", "LED light lamp"),
            CatalogEntry("LedBar", "LED bar", "LEDs bar graph"),
            CatalogEntry("HexDigit", "Hex-digit", "hex digit display number"),
            CatalogEntry("SevenSegment", "7-Seg", "seven segment display"),
            CatalogEntry("HD44780", "LCD 16x2", "HD44780 LCD character display text 1602"),
            CatalogEntry("Buzzer", "Buzzer", "sound tone speaker beep"),
            CatalogEntry("LogicAnalyzer", "Logic Analyzer", "logic analyzer waveform plot"),
            CatalogEntry("Probe", "Probe", "probe value meter show"),
        ],
    ),
    (
        "Gates",
        [
            CatalogEntry("OR", "OR", "or gate"),
            CatalogEntry("AND", "AND", "and gate"),
            CatalogEntry("NOT", "NOT", "not gate inverter"),
            CatalogEntry("XOR", "XOR", "xor gate exclusive or"),
            CatalogEntry("XNOR", "XNOR", "xnor gate exclusive nor"),
            CatalogEntry("NAND", "NAND", "nand gate"),
            CatalogEntry("NOR", "NOR", "nor gate"),
            CatalogEntry("DFF", "DFF", "D flip-flop register latch store"),
            CatalogEntry("FlipFlop", "FlipFlop", "flip-flop JK SR T latch"),
            CatalogEntry("Counter", "Counter", "counter count up down register"),
            CatalogEntry("MUX", "MUX", "multiplexer mux select"),
            CatalogEntry("Decoder", "Decoder", "decoder select one hot address"),
            CatalogEntry("Demultiplexer", "Demux", "demultiplexer demux select"),
        ],
    ),
    (
        "Arithmetic",
        [
            CatalogEntry("Adder", "Adder", "adder add sum plus carry"),
            CatalogEntry("Subtractor", "Subtractor", "subtractor subtract minus borrow"),
            CatalogEntry("Multiplier", "Multiplier", "multiplier multiply product times"),
            CatalogEntry("Comparator", "Comparator", "comparator compare less equal greater"),
            CatalogEntry("Negator", "Negator", "negator negate minus two's complement"),
        ],
    ),
    (
        "Bus / Wires",
        [
            CatalogEntry("LabelWireIn", "Wire Sink", "wire sink label tunnel"),
            CatalogEntry("LabelWireOut", "Wire Source", "wire source label tunnel"),
            CatalogEntry("Bus2Wires", "Bus2Wires", "bus splitter split wires bits"),
            CatalogEntry("Wires2Bus", "Wires2Bus", "bus merge join wires bits"),
            CatalogEntry("Splitter", "Splitter", "bus splitter split merge join groups bits"),
            CatalogEntry("TristateBuffer", "Tristate Buffer", "tristate buffer enable bus"),
        ],
    ),
    (
        "Memory",
        [
            CatalogEntry("RAM", "RAM", "ram memory"),
            CatalogEntry("ROM", "ROM", "rom memory"),
        ],
    ),
    (
        "Circuit ports",
        [
            CatalogEntry("CircuitInput", "In", "circuit port input pin interface subcircuit"),
            CatalogEntry("CircuitOutput", "Out", "circuit port output pin interface subcircuit"),
            CatalogEntry("CircuitInOut", "InOut", "circuit port inout pin interface subcircuit"),
        ],
    ),
    (
        "IC / Verilog",
        [
            CatalogEntry("IntegratedCircuit", "IC", "IC chip 74xx 4000 integrated circuit"),
            CatalogEntry("YosysComponent", "Verilog", "Verilog Yosys netlist synthesis"),
            CatalogEntry("SubCircuit", "Subcircuit", "subcircuit circuit file part hierarchy"),
        ],
    ),
    (
        "Other",
        [
            CatalogEntry("Note", "Note", "note text comment"),
        ],
    ),
]

CATALOG: dict[str, CatalogEntry] = {
    entry.name: entry for _, entries in COMPONENT_GROUPS for entry in entries
}


def search_components(query: str) -> list[CatalogEntry]:
    """
    The components that match a query, the best match first: each word must match the
    name shown or a keyword, also with skipped letters. An empty query matches none.
    """
    if not query.strip():
        return []
    # By the name shown, and the class name and keywords as the description
    items = {entry.display_name: f"{entry.name} {entry.keywords}" for entry in CATALOG.values()}
    by_display_name = {entry.display_name: entry for entry in CATALOG.values()}
    found = [by_display_name[name] for name in fuzzy_search(query, items)]
    # The component with exactly that name first, "led" is the LED and not the LED bar
    exact = query.strip().lower()
    return sorted(
        found, key=lambda entry: exact not in (entry.name.lower(), entry.display_name.lower())
    )
