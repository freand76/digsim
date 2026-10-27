# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the lines and the data of copied components"""

from digsim.app._clipboard_lines import lines_between, moved_lines
from digsim.storage_model import ClipboardDataClass, ComponentDataClass, LineDataClass


# A button that drives two LEDs, the line goes right from the button and splits at p1
LINE = LineDataClass(
    ports=["Button.O", "LedA.I", "LedB.I"],
    points={"p1": [100, 50], "p2": [100, 90]},
    segments=[["Button.O", "p1"], ["p1", "LedA.I"], ["p1", "p2"], ["p2", "LedB.I"]],
)


def test_lines_between_the_copied_ports():
    """The segments to the ports that aren't copied go"""
    (line,) = lines_between([LINE], {"Button.O", "LedA.I"}, {})
    assert sorted(line.ports) == ["Button.O", "LedA.I"]
    assert ["p2", "LedB.I"] not in line.segments
    assert all("LedB.I" not in segment for segment in line.segments)


def test_lines_between_one_port_connect_nothing():
    """A line with only one copied port is left out, and so is a line of other ports"""
    assert lines_between([LINE], {"Button.O"}, {}) == []
    assert lines_between([LINE], {"Other.O", "Other.I"}, {}) == []


def test_lines_between_through_another_port():
    """A line that goes on from the port of a component that isn't copied still does"""
    # From the button to LedA's input, and on from there to LedB
    line = LineDataClass(
        ports=["Button.O", "LedA.I", "LedB.I"],
        points={"p1": [200, 50]},
        segments=[["Button.O", "LedA.I"], ["LedA.I", "p1"], ["p1", "LedB.I"]],
    )
    (part,) = lines_between([line], {"Button.O", "LedB.I"}, {"LedA.I": [150, 50]})
    assert part.ports == ["Button.O", "LedB.I"]
    assert len(part.segments) == 3
    (through,) = [node for node in part.points if node != "p1"]
    assert part.points[through] == [150, 50]
    # Without its place, the segments to it go, the ports are still on one line
    (part,) = lines_between([line], {"Button.O", "LedB.I"}, {})
    assert part.ports == ["Button.O", "LedB.I"]
    assert part.segments == []


def test_moved_lines():
    """The ports get the new names of their components, the points move"""
    (line,) = moved_lines([LINE], {"Button": "Button_1", "LedA": "LedA_1"}, 20, 40)
    assert line.ports == ["Button_1.O", "LedA_1.I", "LedB.I"]
    assert line.points == {"p1": [120, 90], "p2": [120, 130]}
    assert line.segments[0] == ["Button_1.O", "p1"]
    assert line.segments[1] == ["p1", "LedA_1.I"]


def test_clipboard_json():
    """The data goes through JSON, other text isn't DigSim components"""
    data = ClipboardDataClass(
        components=[ComponentDataClass(name="Led", type="digsim.circuit.components.Led")],
        lines=[LINE],
    )
    assert ClipboardDataClass.from_json(data.to_json()) == data
    assert ClipboardDataClass.from_json("hello") is None
    assert ClipboardDataClass.from_json("[1, 2]") is None
    assert ClipboardDataClass.from_json('{"components": []}') is None
    assert ClipboardDataClass.from_json('{"digsim_clipboard": 1, "components": 5}') is None
