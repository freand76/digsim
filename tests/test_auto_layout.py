# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Edit > Auto Layout: the components in columns, the lines drawn again between them"""

from digsim.app._auto_layout import _normalized, auto_layout
from digsim.app._netlist_layout import NodeShape


def _shapes() -> dict[str, NodeShape]:
    return {
        "switch": NodeShape(40, 40, {"O": (40, 20)}),
        "button": NodeShape(40, 40, {"O": (40, 20)}),
        "and": NodeShape(60, 40, {"A": (0, 10), "B": (0, 30), "Y": (60, 20)}),
        "led": NodeShape(30, 40, {"I": (0, 20)}),
        "note": NodeShape(200, 50, {}),
    }


def _lines() -> list[tuple[list[str], set[str]]]:
    return [
        (["switch.O", "and.A"], {"switch.O"}),
        (["button.O", "and.B"], {"button.O"}),
        (["and.Y", "led.I"], {"and.Y"}),
    ]


def _reached(line, start: str) -> set[str]:
    """The ports and points that a line's segments reach from one of its ports"""
    neighbors: dict[str, set[str]] = {}
    for first, second in line.segments:
        neighbors.setdefault(first, set()).add(second)
        neighbors.setdefault(second, set()).add(first)
    reached = {start}
    todo = [start]
    while todo:
        for node in neighbors.get(todo.pop(), set()):
            if node not in reached:
                reached.add(node)
                todo.append(node)
    return reached


def test_the_inputs_are_left_of_the_gate_and_the_outputs_right():
    result = auto_layout(_shapes(), _lines(), (100, 100))
    x = {name: position[0] for name, position in result.positions.items()}
    assert x["switch"] < x["and"] < x["led"]
    assert x["button"] == x["switch"]
    # At the origin, in whole pixels
    assert min(x.values()) == 100
    assert all(isinstance(v, int) for position in result.positions.values() for v in position)


def test_each_line_is_drawn_from_port_to_port():
    shapes = _shapes()
    result = auto_layout(shapes, _lines(), (0, 0))
    for line, (ports, _) in zip(result.lines, _lines(), strict=True):
        assert line.ports == ports
        assert ports[1] in _reached(line, ports[0])
        for first, second in line.segments:
            a = line.points.get(first)
            b = line.points.get(second)
            if a is not None and b is not None:
                assert a[0] == b[0] or a[1] == b[1]


def test_components_without_wires_go_below():
    result = auto_layout(_shapes(), _lines(), (0, 0))
    wired_bottom = max(
        result.positions[name][1] + _shapes()[name].height for name in ("switch", "and", "led")
    )
    assert result.positions["note"][1] > wired_bottom


def test_a_line_with_two_outputs_reaches_both():
    shapes = {
        "a": NodeShape(40, 40, {"Y": (40, 20)}),
        "b": NodeShape(40, 40, {"Y": (40, 20)}),
        "led": NodeShape(30, 40, {"I": (0, 20)}),
    }
    lines = [(["a.Y", "b.Y", "led.I"], {"a.Y", "b.Y"})]
    (line,) = auto_layout(shapes, lines, (0, 0)).lines
    assert {"b.Y", "led.I"} <= _reached(line, "a.Y")


def test_overlapping_segments_are_split_where_they_meet():
    segments = [((0, 0), (40, 0)), ((20, 0), (40, 0)), ((20, 0), (20, 30))]
    assert sorted(_normalized(segments)) == [
        ((0, 0), (20, 0)),
        ((20, 0), (20, 30)),
        ((20, 0), (40, 0)),
    ]


def test_a_bundle_of_parallel_wires_is_straight():
    # Eight wires from a splitter to a LED bar, past a tall display wired from elsewhere
    pins = {str(bit): (0.0, 10.0 + 10 * bit) for bit in range(8)}
    shapes = {
        "bus": NodeShape(
            30, 90, {"bus": (0, 45), **{f"b{bit}": (30, 10 + 10 * bit) for bit in range(8)}}
        ),
        "source": NodeShape(40, 40, {"O": (40, 20)}),
        "other": NodeShape(40, 40, {"O": (40, 20)}),
        "bar": NodeShape(30, 90, pins),
        "display": NodeShape(200, 250, {"I": (0, 20)}),
    }
    lines = [(["source.O", "bus.bus"], {"source.O"}), (["other.O", "display.I"], {"other.O"})]
    lines += [([f"bus.b{bit}", f"bar.{bit}"], {f"bus.b{bit}"}) for bit in range(8)]
    result = auto_layout(shapes, lines, (0, 0))
    assert result.positions["bar"][1] == result.positions["bus"][1]
    for line in result.lines[2:]:
        ys = {point[1] for point in line.points.values()}
        assert len(ys) <= 1


def test_a_port_on_the_top_is_reached_from_above():
    shapes = {
        "switch": NodeShape(40, 40, {"O": (40, 20)}),
        "lcd": NodeShape(200, 100, {"RS": (50, 0), "E": (60, 0)}),
    }
    lines = [(["switch.O", "lcd.RS", "lcd.E"], {"switch.O"})]
    result = auto_layout(shapes, lines, (0, 0), {"lcd": {"RS": "up", "E": "up"}})
    (line,) = result.lines
    lcd_x, lcd_y = result.positions["lcd"]
    # Into each port from above, not along the top of the LCD
    for port, x in (("lcd.RS", lcd_x + 50), ("lcd.E", lcd_x + 60)):
        ends = [
            line.points[other]
            for first, second in line.segments
            for other in (first, second)
            if port in (first, second) and other != port
        ]
        assert ends and all(end[0] == x and end[1] < lcd_y for end in ends)


def test_the_components_without_wires_wrap_in_rows():
    shapes = _shapes()
    shapes.update({f"note{index}": NodeShape(300, 50, {}) for index in range(6)})
    result = auto_layout(shapes, _lines(), (0, 0))
    rows = {result.positions[f"note{index}"][1] for index in range(6)}
    assert len(rows) > 1


def test_the_same_circuit_gets_the_same_layout():
    # The lines in another order, like after the wires were drawn again
    lines = [(ports[::-1], outputs) for ports, outputs in reversed(_lines())]
    first = auto_layout(_shapes(), _lines(), (0, 0))
    second = auto_layout(_shapes(), lines, (0, 0))
    assert first.positions == second.positions
    # Laid out again from where it is, it stays there
    assert auto_layout(_shapes(), _lines(), (0, 0)).positions == first.positions
