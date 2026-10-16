# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Generate the images for the examples documentation (docs/examples.md):

 * Schematics (SVG) of the circuits built by the Python examples
 * Waveforms (SVG) from the VCD files written by the Python examples
 * Screenshots (PNG) of the GUI example circuits

Run from the repository root:

    uv run --with pytest python docs/scripts/generate_examples.py
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import chdir
from dataclasses import dataclass, field
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "images" / "examples"

# Colors, shared by schematics and waveforms
BG = "#ffffff"
BORDER = "#d0d7de"
TEXT = "#1f2328"
MUTED = "#59636e"
WIRE = "#1f2328"
WAVE = "#1a7f37"
BUS_FILL = "#dafbe1"
UNKNOWN = "#cf222e"
GRID = "#eaeef2"
FONT = "font-family='Helvetica, Arial, sans-serif'"


# --------------------------------------------------------------------------------------
# VCD parsing
# --------------------------------------------------------------------------------------


@dataclass
class Signal:
    width: int
    changes: list[tuple[int, int | str]] = field(default_factory=list)

    def value_at(self, time: int) -> int | str:
        value: int | str = "X"
        for change_time, change_value in self.changes:
            if change_time > time:
                break
            value = change_value
        return value


def parse_vcd(path: Path) -> tuple[dict[str, Signal], int]:
    """Parse a VCD file into {'scope.name': Signal} and the last timestamp"""
    signals: dict[str, Signal] = {}
    by_id: dict[str, list[Signal]] = {}
    scope: list[str] = []
    time = 0
    tokens = path.read_text().split()
    idx = 0

    def parse_value(raw: str) -> int | str:
        try:
            return int(raw, 2)
        except ValueError:
            return "X"

    while idx < len(tokens):
        token = tokens[idx]
        if token == "$scope":
            scope.append(tokens[idx + 2])
            idx += 4
        elif token == "$upscope":
            scope.pop()
            idx += 2
        elif token == "$var":
            width, ident, name = int(tokens[idx + 2]), tokens[idx + 3], tokens[idx + 4]
            signal = Signal(width)
            signals[".".join([*scope, name])] = signal
            by_id.setdefault(ident, []).append(signal)
            idx += 6
        elif token.startswith("$"):
            # Skip other sections ($date, $timescale, $dumpvars, ...)
            if token in ("$dumpvars", "$end", "$enddefinitions"):
                idx += 1
            else:
                while tokens[idx] != "$end":
                    idx += 1
                idx += 1
        elif token.startswith("#"):
            time = int(token[1:])
            idx += 1
        elif token[0] in "bB":
            for signal in by_id.get(tokens[idx + 1], []):
                signal.changes.append((time, parse_value(token[1:])))
            idx += 2
        else:
            for signal in by_id.get(token[1:], []):
                signal.changes.append((time, parse_value(token[0])))
            idx += 1
    return signals, time


def _svg_start(width: float, height: float) -> list[str]:
    """SVG header and a rounded background card"""
    return [
        (
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' "
            f"viewBox='0 0 {width} {height}' {FONT} font-size='12'>"
        ),
        (
            f"<rect x='0.5' y='0.5' width='{width - 1}' height='{height - 1}' rx='6' "
            f"fill='{BG}' stroke='{BORDER}'/>"
        ),
    ]


# --------------------------------------------------------------------------------------
# Waveform rendering
# --------------------------------------------------------------------------------------

UNITS = [(1_000_000_000, "s"), (1_000_000, "ms"), (1_000, "µs"), (1, "ns")]


def _nice_step(span: int, max_ticks: int = 10) -> int:
    raw = span / max_ticks
    magnitude = 10 ** max(0, len(str(int(raw))) - 1)
    for factor in (1, 2, 5, 10):
        if magnitude * factor >= raw:
            return magnitude * factor
    return magnitude * 10


def _format_time(time_ns: int, step: int) -> str:
    for scale, unit in UNITS:
        if step >= scale:
            value = time_ns / scale
            return f"{value:g} {unit}"
    return f"{time_ns} ns"


def render_waves(
    vcd: Path,
    rows: list[tuple[str, str]],
    out: Path,
    start: int = 0,
    end: int | None = None,
    radix: str = "dec",
    width: int = 900,
) -> None:
    """Render selected signals ([(label, 'scope.name')]) of a VCD file to an SVG file"""
    signals, last_time = parse_vcd(vcd)
    end = end if end is not None else last_time
    label_w, row_h, high, top = 140, 34, 22, 12
    plot_w = width - label_w - 20
    height = top + row_h * len(rows) + 34

    def x_of(time: int) -> float:
        return label_w + (min(max(time, start), end) - start) / (end - start) * plot_w

    parts = _svg_start(width, height)
    step = _nice_step(end - start)
    tick = start - start % step
    axis_y = top + row_h * len(rows) + 6
    # Zoomed-in windows far from t=0 get tick labels relative to the window start
    origin = start if start > 20 * step else 0
    if origin:
        parts.append(
            f"<text x='10' y='{axis_y + 16}' fill='{MUTED}' font-size='11'>"
            f"t = {escape(_format_time(origin, origin))} +</text>"
        )
    while tick <= end:
        if tick >= start:
            x = x_of(tick)
            parts.append(
                f"<line x1='{x:.1f}' y1='{top}' x2='{x:.1f}' y2='{axis_y}' stroke='{GRID}'/>"
            )
            parts.append(
                f"<text x='{x:.1f}' y='{axis_y + 16}' text-anchor='middle' fill='{MUTED}' "
                f"font-size='11'>{escape(_format_time(tick - origin, step))}</text>"
            )
        tick += step

    for row, (label, key) in enumerate(rows):
        signal = signals[key]
        y_low = top + row * row_h + (row_h + high) / 2
        y_high = y_low - high
        parts.append(
            f"<text x='10' y='{(y_low + y_high) / 2 + 4:.1f}' fill='{TEXT}'>{escape(label)}</text>"
        )
        # Value segments within the window
        segments: list[tuple[int, int, int | str]] = []
        value = signal.value_at(start)
        seg_start = start
        for change_time, change_value in signal.changes:
            if change_time <= start or change_value == value:
                continue
            if change_time >= end:
                break
            segments.append((seg_start, change_time, value))
            seg_start, value = change_time, change_value
        segments.append((seg_start, end, value))

        if signal.width == 1:
            points: list[str] = []
            for seg_from, seg_to, seg_value in segments:
                if seg_value == "X":
                    parts.append(
                        f"<rect x='{x_of(seg_from):.1f}' y='{y_high}' "
                        f"width='{x_of(seg_to) - x_of(seg_from):.1f}' height='{high}' "
                        f"fill='{UNKNOWN}' fill-opacity='0.15'/>"
                    )
                    continue
                y = y_high if seg_value else y_low
                points += [f"{x_of(seg_from):.1f},{y}", f"{x_of(seg_to):.1f},{y}"]
            if points:
                parts.append(
                    f"<polyline points='{' '.join(points)}' fill='none' stroke='{WAVE}' "
                    f"stroke-width='1.6'/>"
                )
        else:
            mid = (y_low + y_high) / 2
            for seg_from, seg_to, seg_value in segments:
                x1, x2 = x_of(seg_from), x_of(seg_to)
                slant = min(3.0, (x2 - x1) / 2)
                color = UNKNOWN if seg_value == "X" else WAVE
                fill = "#ffebe9" if seg_value == "X" else BUS_FILL
                parts.append(
                    f"<polygon points='{x1:.1f},{mid} {x1 + slant:.1f},{y_high} "
                    f"{x2 - slant:.1f},{y_high} {x2:.1f},{mid} {x2 - slant:.1f},{y_low} "
                    f"{x1 + slant:.1f},{y_low}' fill='{fill}' stroke='{color}' stroke-width='1'/>"
                )
                text = (
                    "X"
                    if seg_value == "X"
                    else (f"{seg_value:X}" if radix == "hex" else str(seg_value))
                )
                if x2 - x1 > 7 * len(text) + 6:
                    parts.append(
                        f"<text x='{(x1 + x2) / 2:.1f}' y='{mid + 4:.1f}' text-anchor='middle' "
                        f"fill='{TEXT}' font-size='11'>{escape(text)}</text>"
                    )
    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Schematic rendering
# --------------------------------------------------------------------------------------


@dataclass
class Box:
    name: str
    kind: str
    x: float
    y: float
    w: float
    h: float
    ins: list[str] = field(default_factory=list)
    outs: list[str] = field(default_factory=list)

    def port(self, name: str) -> tuple[float, float]:
        if name in self.ins:
            idx, ports, x = self.ins.index(name), self.ins, self.x
        else:
            idx, ports, x = self.outs.index(name), self.outs, self.x + self.w
        return x, self.y + self.h * (idx + 1) / (len(ports) + 1)


@dataclass
class Wire:
    src: str  # "box.port"
    dst: str  # "box.port"
    via: list[tuple[float, float]] = field(default_factory=list)
    bus: str = ""  # bus width label, e.g. "16"
    mid_x: float | None = None


def render_schematic(
    boxes: list[Box],
    wires: list[Wire],
    out: Path,
    width: int,
    height: int,
    dots: list[tuple[float, float]] | None = None,
    notes: list[tuple[float, float, str]] | None = None,
) -> None:
    """Render a block schematic to an SVG file"""
    by_name = {box.name: box for box in boxes}

    def endpoint(ref: str) -> tuple[float, float]:
        box_name, port = ref.split(".", 1)
        return by_name[box_name].port(port)

    parts = _svg_start(width, height)
    for wire in wires:
        (sx, sy), (dx, dy) = endpoint(wire.src), endpoint(wire.dst)
        if wire.via:
            points = [(sx, sy), *wire.via, (dx, dy)]
        else:
            mx = wire.mid_x if wire.mid_x is not None else (sx + dx) / 2
            points = [(sx, sy), (mx, sy), (mx, dy), (dx, dy)]
        stroke = 3 if wire.bus else 1.5
        parts.append(
            f"<polyline points='{' '.join(f'{x:.1f},{y:.1f}' for x, y in points)}' "
            f"fill='none' stroke='{WIRE}' stroke-width='{stroke}'/>"
        )
        if wire.bus:
            lx, ly = (points[-2][0] + points[-1][0]) / 2, points[-1][1]
            parts.append(
                f"<line x1='{lx - 4:.1f}' y1='{ly + 5:.1f}' x2='{lx + 4:.1f}' y2='{ly - 5:.1f}' "
                f"stroke='{WIRE}' stroke-width='1.2'/>"
                f"<text x='{lx + 5:.1f}' y='{ly - 6:.1f}' fill='{MUTED}' "
                f"font-size='10'>{escape(wire.bus)}</text>"
            )
    for x, y in dots or []:
        parts.append(f"<circle cx='{x}' cy='{y}' r='3.2' fill='{WIRE}'/>")
    for box in boxes:
        parts.append(
            f"<rect x='{box.x}' y='{box.y}' width='{box.w}' height='{box.h}' rx='5' "
            f"fill='#f6f8fa' stroke='{TEXT}' stroke-width='1.3'/>"
        )
        parts.append(
            f"<text x='{box.x + box.w / 2}' y='{box.y - 6}' text-anchor='middle' "
            f"fill='{MUTED}' font-size='11'>{escape(box.name)}</text>"
        )
        # Larger boxes with ports on both sides get the type name at the bottom
        if box.ins and box.outs and box.h >= 80:
            center_y = box.y + box.h - 12
        else:
            center_y = box.y + box.h / 2 + 4
        parts.append(
            f"<text x='{box.x + box.w / 2}' y='{center_y}' text-anchor='middle' "
            f"fill='{TEXT}' font-weight='bold'>{escape(box.kind)}</text>"
        )
        for port in box.ins:
            x, y = box.port(port)
            parts.append(
                f"<text x='{x + 5}' y='{y + 4}' fill='{TEXT}' font-size='10'>{escape(port)}</text>"
            )
        for port in box.outs:
            x, y = box.port(port)
            parts.append(
                f"<text x='{x - 5}' y='{y + 4}' text-anchor='end' fill='{TEXT}' "
                f"font-size='10'>{escape(port)}</text>"
            )
    for x, y, text in notes or []:
        parts.append(
            f"<text x='{x}' y='{y}' fill='{MUTED}' font-size='11' "
            f"font-style='italic'>{escape(text)}</text>"
        )
    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def button(name: str, x: float, y: float) -> Box:
    return Box(name, "PushButton", x, y, 100, 40, outs=["O"])


def led(name: str, x: float, y: float) -> Box:
    return Box(name, "Led", x, y, 70, 40, ins=["I"])


def schematics() -> None:
    """Schematics of the circuits that the Python examples build"""
    # example_sr.py
    render_schematic(
        [
            button("S-Button", 20, 40),
            button("R-Button", 20, 120),
            Box("SR", "SR latch", 220, 50, 120, 100, ins=["S", "R"], outs=["Q", "nQ"]),
            led("D1", 420, 60),
        ],
        [Wire("S-Button.O", "SR.S"), Wire("R-Button.O", "SR.R"), Wire("SR.Q", "D1.I")],
        OUT / "sr_circuit.svg",
        520,
        180,
    )
    # example_clock.py
    render_schematic(
        [Box("Clock", "Clock 20 Hz", 20, 40, 120, 40, outs=["O"]), led("D1", 220, 40)],
        [Wire("Clock.O", "D1.I")],
        OUT / "clock_circuit.svg",
        320,
        110,
    )
    # load_save/example_save_circuit.py
    render_schematic(
        [
            button("Button", 20, 100),
            Box("not1", "NOT", 170, 30, 70, 40, ins=["A"], outs=["Y"]),
            Box("not2", "NOT", 290, 30, 70, 40, ins=["A"], outs=["Y"]),
            Box("not3", "NOT", 410, 30, 70, 40, ins=["A"], outs=["Y"]),
            Box("AND", "AND", 540, 90, 70, 60, ins=["A", "B"], outs=["Y"]),
            led("D", 670, 100),
        ],
        [
            Wire("Button.O", "not1.A", mid_x=140),
            Wire("Button.O", "AND.A", via=[(140, 120), (140, 110), (540, 110)]),
            Wire("not1.Y", "not2.A"),
            Wire("not2.Y", "not3.A"),
            Wire("not3.Y", "AND.B", mid_x=510),
            Wire("AND.Y", "D.I"),
        ],
        OUT / "pulse_circuit.svg",
        770,
        180,
        dots=[(140, 120)],
    )
    # load_save/example_load_circuit.py (example_circuit.json)
    render_schematic(
        [
            button("button1", 20, 60),
            button("button2", 20, 200),
            Box("and1", "AND", 250, 30, 70, 60, ins=["A", "B"], outs=["Y"]),
            Box("not1", "NOT", 250, 120, 70, 40, ins=["A"], outs=["Y"]),
            Box("xor1", "XOR", 250, 190, 70, 60, ins=["A", "B"], outs=["Y"]),
            led("and_led", 400, 40),
            led("not_led", 400, 120),
            led("xor_led", 400, 200),
        ],
        [
            Wire("button1.O", "and1.A", mid_x=160),
            Wire("button1.O", "not1.A", mid_x=160),
            Wire("button1.O", "xor1.A", mid_x=160),
            Wire("button2.O", "and1.B", mid_x=200),
            Wire("button2.O", "xor1.B", mid_x=200),
            Wire("and1.Y", "and_led.I"),
            Wire("not1.Y", "not_led.I"),
            Wire("xor1.Y", "xor_led.I"),
        ],
        OUT / "load_circuit.svg",
        500,
        280,
        dots=[(160, 80), (160, 140), (200, 220)],
    )
    # yosys_counter/example_yosys_counter_*.py
    render_schematic(
        [
            button("clk", 20, 30),
            button("reset", 20, 90),
            Box("VDD", "VDD", 20, 150, 100, 40, outs=["O"]),
            Box(
                "counter",
                "counter (Yosys)",
                220,
                40,
                150,
                140,
                ins=["clk", "reset", "up"],
                outs=["cnt"],
            ),
        ],
        [
            Wire("clk.O", "counter.clk"),
            Wire("reset.O", "counter.reset"),
            Wire("VDD.O", "counter.up"),
        ],
        OUT / "counter_circuit.svg",
        520,
        210,
        notes=[(380, 104, "cnt[3:0] → printed")],
    )
    # synthesis/example_synthesis.py
    render_schematic(
        [
            Box("script", "Python script", 20, 50, 130, 80, outs=["clk", "reset"]),
            Box(
                "fibonacci",
                "fibonacci (Yosys)",
                230,
                50,
                160,
                80,
                ins=["clk", "reset"],
                outs=["index", "value"],
            ),
        ],
        [Wire("script.clk", "fibonacci.clk"), Wire("script.reset", "fibonacci.reset")],
        OUT / "fibonacci_circuit.svg",
        560,
        170,
        notes=[(400, 80, "index[15:0] → printed"), (400, 110, "value[15:0] → printed")],
    )
    # yosys_6502/example_yosys_6502.py
    cpu = Box(
        "cpu",
        "6502 (Yosys)",
        240,
        40,
        150,
        250,
        ins=["clk", "reset", "IRQ", "NMI", "RDY", "DI"],
        outs=["AB", "DO", "WE"],
    )
    mem = Box(
        "Memory",
        "Mem64kByte",
        580,
        30,
        170,
        150,
        ins=["clk", "Address", "DataIn", "WE"],
        outs=["DataOut"],
    )
    out = Box("MemStdOut", "MemStdOut", 580, 210, 170, 130, ins=["clk", "Address", "DataIn", "WE"])

    def py(box: Box, port: str) -> float:
        return box.port(port)[1]

    render_schematic(
        [
            Box("CLK", "Clock 1 MHz", 20, 40, 130, 40, outs=["O"]),
            Box("RST", "PushButton", 20, 100, 130, 40, outs=["O"]),
            Box("IRQ", "StaticValue 0", 20, 160, 130, 40, outs=["O"]),
            Box("RDY", "StaticValue 1", 20, 220, 130, 40, outs=["O"]),
            cpu,
            mem,
            out,
        ],
        [
            Wire("CLK.O", "cpu.clk", mid_x=185),
            Wire(
                "CLK.O", "Memory.clk", via=[(185, 60), (185, 18), (540, 18), (540, py(mem, "clk"))]
            ),
            Wire(
                "CLK.O",
                "MemStdOut.clk",
                via=[(185, 60), (185, 18), (540, 18), (540, py(out, "clk"))],
            ),
            Wire("RST.O", "cpu.reset", mid_x=210),
            Wire("IRQ.O", "cpu.IRQ", mid_x=200),
            Wire("IRQ.O", "cpu.NMI", mid_x=200),
            Wire("RDY.O", "cpu.RDY", mid_x=210),
            Wire("cpu.AB", "Memory.Address", mid_x=460, bus="16"),
            Wire("cpu.AB", "MemStdOut.Address", mid_x=460, bus="16"),
            Wire("cpu.DO", "Memory.DataIn", mid_x=480, bus="8"),
            Wire("cpu.DO", "MemStdOut.DataIn", mid_x=480, bus="8"),
            Wire("cpu.WE", "Memory.WE", mid_x=500),
            Wire("cpu.WE", "MemStdOut.WE", mid_x=500),
            Wire(
                "Memory.DataOut",
                "cpu.DI",
                via=[(775, py(mem, "DataOut")), (775, 345), (225, 345), (225, py(cpu, "DI"))],
                bus="8",
            ),
        ],
        OUT / "6502_circuit.svg",
        800,
        360,
        dots=[
            (185, 60),
            (540, py(mem, "clk")),
            (200, 180),
            (460, py(cpu, "AB")),
            (480, py(cpu, "DO")),
            (500, py(cpu, "WE")),
        ],
    )
    # pytest_tb
    render_schematic(
        [
            Box("pytest", "pytest", 20, 40, 110, 100, outs=["clk", "nrst", "up", "down"]),
            Box(
                "dut",
                "up_down_counter",
                210,
                40,
                160,
                100,
                ins=["clk", "nrst", "up", "down"],
                outs=["value"],
            ),
            Box("check", "pytest", 450, 70, 90, 40, ins=["assert"]),
        ],
        [
            Wire("pytest.clk", "dut.clk"),
            Wire("pytest.nrst", "dut.nrst"),
            Wire("pytest.up", "dut.up"),
            Wire("pytest.down", "dut.down"),
            Wire("dut.value", "check.assert", bus="4"),
        ],
        OUT / "testbench_circuit.svg",
        570,
        170,
    )


# --------------------------------------------------------------------------------------
# Running the examples
# --------------------------------------------------------------------------------------

EXAMPLES = [
    "examples/example_sr.py",
    "examples/example_clock.py",
    "examples/load_save/example_save_circuit.py",
    "examples/load_save/example_load_circuit.py",
    "examples/yosys_counter/example_yosys_counter_netlist.py",
    "examples/synthesis/example_synthesis.py",
    "examples/yosys_6502/example_yosys_6502.py --vcd",
]


def run_examples(vcd_dir: Path) -> None:
    """Run the examples (from the repository root) and collect their VCD files"""
    before = set(glob.glob(str(ROOT / "**/*"), recursive=True))
    for example in EXAMPLES:
        subprocess.run(
            [sys.executable, *example.split()], cwd=ROOT, check=True, capture_output=True
        )
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "examples/pytest_tb"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    for vcd in ROOT.glob("*.vcd"):
        if str(vcd) not in before:
            shutil.move(str(vcd), vcd_dir / vcd.name)
        else:
            shutil.copy(vcd, vcd_dir / vcd.name)
    # Remove other files generated by the examples
    for path in set(glob.glob(str(ROOT / "examples/**/*"), recursive=True)) - before:
        if os.path.isfile(path):
            os.remove(path)


def waves(vcd_dir: Path) -> None:
    ms = 1_000_000
    render_waves(
        vcd_dir / "sr.vcd",
        [
            ("S-Button", "S-Button.O"),
            ("R-Button", "R-Button.O"),
            ("SR.Q", "SR.Q"),
            ("SR.nQ", "SR.nQ"),
            ("D1 (LED)", "D1.I"),
        ],
        OUT / "sr_waves.svg",
        end=70 * ms,
    )
    render_waves(
        vcd_dir / "clock.vcd",
        [("Clock", "Clock.O"), ("D1 (LED)", "D1.I")],
        OUT / "clock_waves.svg",
        end=300 * ms,
    )
    render_waves(
        vcd_dir / "pulse.vcd",
        [
            ("Button", "Button.O"),
            ("not1.Y", "not1.Y"),
            ("not2.Y", "not2.Y"),
            ("not3.Y", "not3.Y"),
            ("AND.Y", "AND.Y"),
        ],
        OUT / "pulse_waves.svg",
        start=10 * ms - 2,
        end=10 * ms + 8,
    )
    render_waves(
        vcd_dir / "circuit.vcd",
        [
            ("button1", "button1.O"),
            ("button2", "button2.O"),
            ("and_led", "and_led.I"),
            ("not_led", "not_led.I"),
            ("xor_led", "xor_led.I"),
        ],
        OUT / "load_waves.svg",
        end=25 * ms,
    )
    render_waves(
        vcd_dir / "counter.vcd",
        [
            ("clk", "counter.clk"),
            ("reset", "counter.reset"),
            ("up", "counter.up"),
            ("cnt", "counter.cnt"),
        ],
        OUT / "counter_waves.svg",
        start=30 * ms,
    )
    render_waves(
        vcd_dir / "fibonacci.vcd",
        [
            ("clk", "fibonacci.clk"),
            ("reset", "fibonacci.reset"),
            ("index", "fibonacci.index"),
            ("value", "fibonacci.value"),
        ],
        OUT / "fibonacci_waves.svg",
        width=1000,
    )
    signals, _ = parse_vcd(vcd_dir / "6502.vcd")
    writes = [
        time
        for time, value in signals["MemStdOut.WE"].changes
        if value == 1 and signals["MemStdOut.Address"].value_at(time) == 0x8000
    ]
    first_write = writes[0] if writes else 0
    render_waves(
        vcd_dir / "6502.vcd",
        [
            ("CLK", "CLK.O"),
            ("cpu.AB", "cpu.AB"),
            ("cpu.DO", "cpu.DO"),
            ("cpu.WE", "cpu.WE"),
            ("Memory.DataOut", "Memory.DataOut"),
        ],
        OUT / "6502_waves.svg",
        start=first_write - 6_000,
        end=first_write + 3_000,
        radix="hex",
        width=1000,
    )
    render_waves(
        vcd_dir / "up_down_counter_test.vcd",
        [
            ("clk", "up_down_counter.clk"),
            ("nrst", "up_down_counter.nrst"),
            ("up", "up_down_counter.up"),
            ("down", "up_down_counter.down"),
            ("value", "up_down_counter.value"),
        ],
        OUT / "testbench_waves.svg",
        end=120 * ms,
        width=1000,
    )


# --------------------------------------------------------------------------------------
# Screenshots of the GUI example circuits
# --------------------------------------------------------------------------------------


def screenshots() -> None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QEventLoop, QRectF, Qt, QTimer
    from PySide6.QtWidgets import QApplication

    from digsim.app.gui import MainWindow
    from digsim.app.gui._circuit_area import CircuitArea
    from digsim.app.model import AppModel
    from digsim.circuit.components import OnOffSwitch, PushButton

    app = QApplication.instance() or QApplication([])
    assert app is not None  # keep the application alive while taking screenshots
    model = AppModel()
    window = MainWindow(model, "docs")
    window.resize(2400, 1500)
    window.show()
    area = window.findChild(CircuitArea)
    area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def spin(ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def simulate(ms: int) -> None:
        """
        Run the simulation for a fixed simulated time, in this thread instead of the
        simulation thread, so that the screenshots are the same every time
        """
        model.objects.circuit.run(ms=ms)
        model.objects.components.update_callback_objects()

    def interact(name: str) -> None:
        """Make each circuit show something interesting before the screenshot"""
        circuit = model.objects.circuit
        components = circuit.get_toplevel_components()
        if name in ("counter_yosys_netlist", "counter_yosys_verilog", "74162_counter"):
            # Enable counting
            for component in components:
                if isinstance(component, OnOffSwitch):
                    component.turn_on()
            simulate(2500)
        elif name == "shift_register":
            # Shift in a single one
            button = circuit.get_component("PushButton")
            assert isinstance(button, PushButton)
            button.push()
            simulate(250)
            button.release()
            simulate(500)
        elif name == "buzzers":
            # Press the third button (screenshot while pressed)
            button = circuit.get_component("PushButton_2")
            assert isinstance(button, PushButton)
            button.push()
            simulate(300)
        else:
            simulate(1000)

    with chdir(ROOT):
        for path in sorted((ROOT / "example_circuits").glob("*.circuit")):
            model.load_circuit(str(path.relative_to(ROOT)))
            simulate(300)
            interact(path.stem)
            spin(200)
            # Grab the whole circuit at 1:1 scale, cropped to its components
            for component_object in model.objects.get_list():
                component_object.setSelected(False)
            # Bounds of the components (the scene also has invisible helper items)
            rect = QRectF()
            for component_object in model.objects.get_list():
                rect = rect.united(component_object.sceneBoundingRect())
            rect = rect.adjusted(-15, -15, 15, 15)
            area.centerOn(rect.center())
            spin(200)
            view_rect = area.mapFromScene(rect).boundingRect()
            area.viewport().grab(view_rect).save(str(OUT / f"{path.stem}.png"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    schematics()
    with tempfile.TemporaryDirectory() as tmp:
        run_examples(Path(tmp))
        waves(Path(tmp))
    screenshots()
    print(f"Images written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
