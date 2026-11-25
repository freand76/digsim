# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Pytest module to test DigSim as a cocotb simulator: the stand-in for cocotb.simulator
without cocotb, and the launcher with cocotb when it is installed
"""

import importlib.util
import itertools
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.cocotb import _simulator as sim
from digsim.cocotb import main
from digsim.cocotb._launcher import _yosys_source


# Yosys and files: also on the other platforms (see .github/workflows)
pytestmark = pytest.mark.sanity

COUNTER = Path(__file__).parent / "verilog" / "cocotb_counter.sv"
TESTBENCH = Path(__file__).parent / "cocotb_tb"


@pytest.fixture(name="scheduler")
def _scheduler():
    """A scheduler with the counter, installed as the simulator"""
    circuit = Circuit()
    top = YosysComponent(circuit, _yosys_source(str(COUNTER)), module="counter")
    scheduler = sim._Scheduler(circuit, top, str(COUNTER), ["digsim", "+seed=1"])
    sim.install(scheduler)
    yield scheduler
    sim._scheduler = None


def _now():
    high, low = sim.get_sim_time()
    return (high << 32) | low


def test_time_declarations_removed():
    """Yosys can't parse timeunit and timeprecision: a copy without them is synthesized"""
    source = Path(_yosys_source(str(COUNTER)))
    assert source != COUNTER.resolve()
    text = source.read_text(encoding="utf-8")
    assert "timeunit" not in text
    assert "timeprecision" not in text
    assert "always_ff" in text


def test_source_without_time_declarations_used_as_it_is():
    """A file that Yosys can parse is synthesized from where it is"""
    source = Path(__file__).parent / "verilog" / "one_module.v"
    assert _yosys_source(str(source)) == str(source.resolve())


def test_handles(scheduler):
    """The top module and its ports, as cocotb finds them"""
    root = sim.get_root_handle(None)
    assert root is scheduler.root
    assert sim.get_root_handle("COUNTER") is root
    assert sim.get_root_handle("other") is None
    assert list(sim.root_iterate()) == [root]
    assert list(sim.package_iterate()) == []
    assert root.get_type() == sim.MODULE
    assert root.get_definition_name() == "counter"
    names = [child.get_name_string() for child in root.iterate(sim.OBJECTS)]
    assert names == ["clk", "rst", "ena", "set", "din", "count"]
    clk = root.get_handle_by_name("clk")
    din = root.get_handle_by_name("din")
    assert root.get_handle_by_name("missing") is None
    assert clk.get_type() == sim.LOGIC
    assert din.get_type() == sim.LOGIC_ARRAY
    assert din.get_type_string() == "GPI_LOGIC_ARRAY"
    assert din.get_fullname_string() == "counter.din"
    assert din.get_range() == (7, 0, sim.RANGE_DOWN)
    assert din.get_num_elems() == 8
    assert sim.get_precision() == -12
    assert sim.get_simulator_product() == "DigSim"
    assert sim.get_simulator_args() == ["digsim", "+seed=1"]


def test_values(scheduler):
    """Reading and writing values, with undefined and not driven ones"""
    din = scheduler.root.get_handle_by_name("din")
    assert din.get_signal_val_binstr() == "XXXXXXXX"
    assert din.get_signal_val_long() == 0
    din.set_signal_val_int(sim._DEPOSIT, 124)
    assert din.get_signal_val_binstr() == "01111100"
    assert din.get_signal_val_long() == 124
    din.set_signal_val_binstr(sim._DEPOSIT, "00000011")
    assert din.get_signal_val_long() == 3
    # A port is undefined or not driven as a whole
    din.set_signal_val_binstr(sim._DEPOSIT, "0000001X")
    assert din.get_signal_val_binstr() == "XXXXXXXX"
    din.set_signal_val_binstr(sim._DEPOSIT, "ZZZZZZZZ")
    assert din.get_signal_val_binstr() == "ZZZZZZZZ"


def test_unsupported_writes(scheduler):
    """Only deposits on inputs: no force, no writes to outputs"""
    din = scheduler.root.get_handle_by_name("din")
    count = scheduler.root.get_handle_by_name("count")
    force = 1
    with pytest.raises(NotImplementedError):
        din.set_signal_val_int(force, 1)
    with pytest.raises(NotImplementedError):
        count.set_signal_val_int(sim._DEPOSIT, 1)


def test_phases(scheduler):
    """The callbacks of a time step come in order: timed, ReadWrite, ReadOnly, NextTimeStep"""
    calls = []

    def readonly():
        calls.append(("readonly", _now()))
        sim.register_nextstep_callback(lambda: calls.append(("nextstep", _now())))
        sim.register_timed_callback(5, lambda: calls.append(("timed", _now())))

    def timed():
        calls.append(("timed", _now()))
        sim.register_rwsynch_callback(lambda: calls.append(("readwrite", _now())))
        sim.register_readonly_callback(readonly)

    sim.register_timed_callback(10, timed)
    sim.register_end_of_sim_time_callback(lambda: calls.append(("end", _now())))
    scheduler.run()
    assert calls == [
        ("timed", 10),
        ("readwrite", 10),
        ("readonly", 10),
        ("nextstep", 15),
        ("timed", 15),
        ("end", 15),
    ]
    assert not sim.is_running()


def test_deregistered_callback(scheduler):
    """A deregistered callback isn't called"""
    calls = []
    callback = sim.register_timed_callback(10, lambda: calls.append("first"))
    sim.register_timed_callback(20, lambda: calls.append("second"))
    callback.deregister()
    scheduler.run()
    assert calls == ["second"]


def test_stop_simulator(scheduler):
    """cocotb stops the simulation: no end of simulation callback, no more callbacks"""
    calls = []

    def stop():
        calls.append("stop")
        sim.stop_simulator()

    sim.register_timed_callback(10, stop)
    sim.register_timed_callback(20, lambda: calls.append("later"))
    sim.register_end_of_sim_time_callback(lambda: calls.append("end"))
    scheduler.run()
    assert calls == ["stop"]


def test_exception_ends_simulation(scheduler, capsys):
    """An exception in a callback ends the simulation, like with the GPI"""
    calls = []

    def fail():
        raise RuntimeError("callback failed")

    sim.register_timed_callback(10, fail)
    sim.register_timed_callback(20, lambda: calls.append("later"))
    sim.register_end_of_sim_time_callback(lambda: calls.append("end"))
    scheduler.run()
    assert calls == ["end"]
    assert "callback failed" in capsys.readouterr().err


def _changes(vcd, name):
    """The (time, value) changes of a one bit variable of a VCD file"""
    lines = vcd.read_text(encoding="utf-8").splitlines()
    ident = next(line.split()[3] for line in lines if line.endswith(f" {name} $end"))
    changes, time = [], 0
    for line in lines:
        if line.startswith("#"):
            time = int(line[1:])
        elif line[1:] == ident and line[0] in "01xX":
            changes.append((time, line[0]))
    return changes


def test_waves(scheduler, tmp_path):
    """The VCD file is in picoseconds, with the changes of the inputs at their times"""
    vcd = tmp_path / "waves.vcd"
    scheduler.circuit.vcd(str(vcd), timescale=sim.TIMESCALE)
    clk = scheduler.root.get_handle_by_name("clk")
    for time, value in ((1000, 1), (2000, 0)):
        sim.register_timed_callback(
            time, lambda value=value: clk.set_signal_val_int(sim._DEPOSIT, value)
        )
    scheduler.run()
    scheduler.circuit.vcd_close()
    assert "$timescale 1 ps $end" in vcd.read_text(encoding="utf-8")
    assert _changes(vcd, "clk") == [(0, "X"), (1000, "1"), (2000, "0")]


def test_long_time(scheduler):
    """The time is split into two 32 bit words"""
    times = []
    sim.register_timed_callback((1 << 32) + 5, lambda: times.append(sim.get_sim_time()))
    scheduler.run()
    assert times == [(1, 5)]


def test_clock_and_edges(scheduler):
    """A cpp_clock drives the clock, rising edges see the flip-flops before they change"""
    root = scheduler.root
    for name, value in (("rst", 1), ("ena", 1), ("set", 0), ("din", 0)):
        root.get_handle_by_name(name).set_signal_val_int(sim._DEPOSIT, value)
    clk = root.get_handle_by_name("clk")
    count = root.get_handle_by_name("count")
    clock = sim.clock_create(clk)
    edges = []

    def rising():
        edges.append((_now(), count.get_signal_val_binstr()))
        root.get_handle_by_name("rst").set_signal_val_int(sim._DEPOSIT, 0)
        if len(edges) == 4:
            clock.stop()
            sim.stop_simulator()
        else:
            sim.register_value_change_callback(clk, rising, sim.RISING)

    sim.register_value_change_callback(clk, rising, sim.RISING)
    clock.start(10_000, 5_000, False, sim._DEPOSIT)
    scheduler.run()
    assert edges == [
        (5_000, "XXXXXXXX"),
        (15_000, "00000000"),
        (25_000, "00000001"),
        (35_000, "00000010"),
    ]


def test_value_change_edges(scheduler):
    """Value change callbacks: on any change, on rising and on falling edges"""
    clk = scheduler.root.get_handle_by_name("clk")
    seen = []

    def watch(edge, name):
        def callback():
            seen.append((name, _now(), clk.get_signal_val_binstr()))
            sim.register_value_change_callback(clk, callback, edge)

        sim.register_value_change_callback(clk, callback, edge)

    watch(sim.VALUE_CHANGE, "change")
    watch(sim.RISING, "rising")
    watch(sim.FALLING, "falling")
    for time, value in ((10, 0), (20, 1), (30, 0)):
        sim.register_timed_callback(
            time, lambda value=value: clk.set_signal_val_int(sim._DEPOSIT, value)
        )
    sim.register_timed_callback(40, sim.stop_simulator)
    scheduler.run()
    # The callbacks of a change come in no particular order
    assert sorted(seen, key=lambda call: (call[1], call[0])) == [
        ("change", 10, "0"),
        ("falling", 10, "0"),
        ("change", 20, "1"),
        ("rising", 20, "1"),
        ("change", 30, "0"),
        ("falling", 30, "0"),
    ]


def test_launcher_arguments(monkeypatch):
    """The launcher rejects arguments that aren't plusargs, and needs the top module"""
    monkeypatch.delenv("COCOTB_TOPLEVEL", raising=False)
    with pytest.raises(SystemExit):
        main([str(COUNTER), "--test-modules", "counter_tb", "--unknown"])
    with pytest.raises(SystemExit):
        main([str(COUNTER), str(COUNTER), "--test-modules", "counter_tb"])


@pytest.mark.skipif(importlib.util.find_spec("cocotb") is None, reason="cocotb isn't installed")
def test_cocotb_testbench(tmp_path):
    """cocotb runs the tests of counter_tb.py on DigSim"""
    results = tmp_path / "results.xml"
    env = dict(os.environ, COCOTB_RESULTS_FILE=str(results))
    for name in ("COCOTB_TOPLEVEL", "COCOTB_TEST_MODULES", "COCOTB_TESTCASE"):
        env.pop(name, None)
    command = [sys.executable, "-m", "digsim.cocotb", str(COUNTER), "--toplevel", "counter"]
    command += ["--test-modules", "counter_tb", "+digsim_plusarg=42"]
    command += ["--waves", str(tmp_path / "counter.vcd")]
    run = subprocess.run(
        command, check=False, cwd=TESTBENCH, env=env, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stdout + run.stderr
    cases = ET.parse(results).getroot().findall(".//testcase")
    assert len(cases) == 5
    failed = [case.get("name") for case in cases if case.find("failure") is not None]
    assert failed == [], run.stdout
    # The 10 ns clocks of the tests, in picoseconds
    changes = _changes(tmp_path / "counter.vcd", "clk")
    assert len(changes) > 20
    assert 5000 in {later - earlier for (earlier, _), (later, _) in itertools.pairwise(changes)}
    # A named signal inside the design, with the values of the counter
    lines = (tmp_path / "counter.vcd").read_text(encoding="utf-8").splitlines()
    ident = next(line.split()[3] for line in lines if line.endswith(" value $end"))
    texts = [line[1:].split()[0] for line in lines if line.endswith(f" {ident}")]
    values = {int(text, 2) for text in texts if set(text) <= {"0", "1"}}
    assert set(range(10, 21)) <= values
