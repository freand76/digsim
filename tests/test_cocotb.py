# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Pytest module to test DigSim as a cocotb simulator: the stand-in for cocotb.simulator
without cocotb, and the launcher with cocotb when it is installed
"""

import argparse
import importlib.util
import itertools
import json
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
from digsim.cocotb._launcher import _define, _parameter, _yosys_source


# Yosys and files: also on the other platforms (see .github/workflows)
pytestmark = pytest.mark.sanity

VERILOG = Path(__file__).parent / "verilog"
COUNTER = VERILOG / "cocotb_counter.sv"
OPTIONS = VERILOG / "cocotb_options.sv"
TESTBENCH = Path(__file__).parent / "cocotb_tb"


@pytest.fixture(name="scheduler")
def _scheduler():
    """A scheduler with the counter, installed as the simulator"""
    circuit = Circuit()
    top = YosysComponent(circuit, _yosys_source(str(COUNTER)), module="counter", signals=True)
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
    assert names == ["clk", "rst", "ena", "set", "din", "count", "odd", "u_parity", "value"]
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


def test_unsupported_writes(scheduler, caplog):
    """
    Only deposits on the inputs of the top module: other writes are logged and ignored,
    like the GPI does with a write that the simulator rejects
    """
    root = scheduler.root
    din = root.get_handle_by_name("din")
    count = root.get_handle_by_name("count")
    value = root.get_handle_by_name("value")
    sub_clk = root.get_handle_by_name("u_parity").get_handle_by_name("clk")
    force = 1
    din.set_signal_val_int(force, 1)
    count.set_signal_val_int(sim._DEPOSIT, 1)
    value.set_signal_val_int(sim._DEPOSIT, 1)
    sub_clk.set_signal_val_int(sim._DEPOSIT, 1)
    for obj in (din, count, value, sub_clk):
        assert set(obj.get_signal_val_binstr()) == {"X"}
    errors = [record.getMessage() for record in caplog.records if record.name == "gpi"]
    assert errors == [
        "DigSim can only deposit values, not force or release counter.din",
        "DigSim can only set the inputs of the top module, not counter.count",
        "DigSim can only set the inputs of the top module, not counter.value",
        "DigSim can only set the inputs of the top module, not counter.u_parity.clk",
    ]


def test_internal_signals(scheduler):
    """The named signals inside the design, also in a submodule, with value changes"""
    root = scheduler.root
    parity = root.get_handle_by_name("u_parity")
    assert parity.get_type() == sim.MODULE
    assert parity.get_fullname_string() == "counter.u_parity"
    odd_reg = parity.get_handle_by_name("odd_reg")
    value = root.get_handle_by_name("value")
    assert odd_reg.get_fullname_string() == "counter.u_parity.odd_reg"
    assert odd_reg.get_type() == sim.LOGIC
    assert value.get_type() == sim.LOGIC_ARRAY
    assert value.get_range() == (7, 0, sim.RANGE_DOWN)
    for name, level in (("rst", 0), ("ena", 0), ("set", 1), ("din", 3)):
        root.get_handle_by_name(name).set_signal_val_int(sim._DEPOSIT, level)
    clk = root.get_handle_by_name("clk")
    clk.set_signal_val_int(sim._DEPOSIT, 0)
    changes = []
    sim.register_value_change_callback(
        value, lambda: changes.append((_now(), value.get_signal_val_long())), sim.VALUE_CHANGE
    )
    sim.register_timed_callback(1000, lambda: clk.set_signal_val_int(sim._DEPOSIT, 1))
    sim.register_timed_callback(2000, lambda: clk.set_signal_val_int(sim._DEPOSIT, 0))
    sim.register_timed_callback(3000, lambda: clk.set_signal_val_int(sim._DEPOSIT, 1))
    sim.register_timed_callback(4000, sim.stop_simulator)
    scheduler.run()
    # The value is loaded at the first edge (after the delays of the gates), its parity
    # (two ones: even) at the next
    assert len(changes) == 1
    assert 1000 < changes[0][0] < 2000
    assert changes[0][1] == 3
    assert root.get_handle_by_name("count").get_signal_val_long() == 3
    assert odd_reg.get_signal_val_binstr() == "0"
    assert root.get_handle_by_name("odd").get_signal_val_binstr() == "0"


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
    assert len(cases) == 7
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


@pytest.mark.parametrize(
    "text, parameter",
    [
        ("WIDTH=8", ("WIDTH", 8)),
        ("WIDTH=0x10", ("WIDTH", 16)),
        ("WIDTH=8'd5", ("WIDTH", 5)),
        ("WIDTH=4'b10_10", ("WIDTH", 10)),
        ("WIDTH='hFF", ("WIDTH", 255)),
    ],
)
def test_parameter_values(text, parameter):
    """Parameters are integers, also as Verilog constants"""
    assert _parameter(text) == parameter


@pytest.mark.parametrize("text", ["WIDTH", "WIDTH=wide", "WIDTH=8'x5"])
def test_bad_parameter_values(text):
    """A parameter without a value, or with a value that isn't an integer"""
    with pytest.raises(argparse.ArgumentTypeError):
        _parameter(text)


def test_defines():
    """A macro with or without a value"""
    assert _define("DEBUG") == ("DEBUG", None)
    assert _define("WIDTH=8") == ("WIDTH", "8")
    assert _define("EMPTY=") == ("EMPTY", "")


def _netlist_module(path):
    module = next(iter(json.loads(path.read_text(encoding="utf-8"))["modules"].values()))
    cells = sorted({cell["type"] for cell in module["cells"].values()})
    return len(module["ports"]["a"]["bits"]), cells


def test_netlist_build_step(tmp_path):
    """--netlist only synthesizes, with include folders, macros and parameters"""
    netlist = tmp_path / "options.json"
    arguments = [str(OPTIONS), "--toplevel", "options", "-I", str(VERILOG / "include")]
    assert main([*arguments, "--netlist", str(netlist)]) == 0
    assert _netlist_module(netlist) == (2, [])
    assert main([*arguments, "-DINVERT", "-PWIDTH=4", "--netlist", str(netlist)]) == 0
    assert _netlist_module(netlist) == (4, ["$_NOT_"])


def test_netlist_string_macro(tmp_path):
    """-D gives a string macro as it is written, with its quotes and spaces"""
    netlist = tmp_path / "string_macro.json"
    source = str(VERILOG / "synth_string_macro.sv")
    text = '-DTEXT="path/to/some (random quote)/a;b#c.wow"'
    assert main([source, "--toplevel", "string_macro", text, "--netlist", str(netlist)]) == 0
    module = json.loads(netlist.read_text(encoding="utf-8"))["modules"]["string_macro"]
    assert module["ports"]["y"]["bits"] == ["1", "0"]


def test_netlist_keeps_signals(tmp_path):
    """The signals that no output depends on are kept for the tests, not with --no-signals"""
    netlist = tmp_path / "keep.json"
    arguments = [str(VERILOG / "synth_keep_signals.sv"), "--toplevel", "keep_signals"]
    assert main([*arguments, "--netlist", str(netlist)]) == 0
    module = json.loads(netlist.read_text(encoding="utf-8"))["modules"]["keep_signals"]
    assert "count_plus_two" in module["netnames"]
    assert main([*arguments, "--no-signals", "--netlist", str(netlist)]) == 0
    module = json.loads(netlist.read_text(encoding="utf-8"))["modules"]["keep_signals"]
    assert "count_plus_two" not in module["netnames"]


def test_netlist_include_from_own_folder(tmp_path):
    """A file synthesized as a copy without its time declarations includes from its folder"""
    netlist = tmp_path / "local.json"
    source = VERILOG / "cocotb_local_include.sv"
    assert main([str(source), "--toplevel", "local_include", "--netlist", str(netlist)]) == 0
    assert _netlist_module(netlist) == (3, [])


def test_netlist_top_module_found(tmp_path):
    """One file without --toplevel: its top module"""
    netlist = tmp_path / "counter.json"
    assert main([str(COUNTER), "--netlist", str(netlist)]) == 0
    assert list(json.loads(netlist.read_text(encoding="utf-8"))["modules"]) == ["counter"]


def test_synthesis_error(tmp_path, capsys, monkeypatch):
    """A synthesis error is printed with the Yosys log, the launcher returns 1"""
    monkeypatch.delenv("COCOTB_TOPLEVEL", raising=False)
    netlist = tmp_path / "options.json"
    assert main([str(OPTIONS), "--toplevel", "options", "--netlist", str(netlist)]) == 1
    error = capsys.readouterr().err
    assert "Yosys:" in error
    assert "DigSim:" in error
    assert "cocotb_options.vh" in error
    assert not netlist.exists()


def test_netlist_arguments(tmp_path, monkeypatch):
    """The netlist is a .json file, and a netlist is simulated as it is"""
    monkeypatch.delenv("COCOTB_TOPLEVEL", raising=False)
    with pytest.raises(SystemExit):
        main([str(COUNTER), "--netlist", str(tmp_path / "counter.txt")])
    netlist = tmp_path / "counter.json"
    assert main([str(COUNTER), "--netlist", str(netlist)]) == 0
    with pytest.raises(SystemExit):
        main([str(netlist), "-PWIDTH=4", "--test-modules", "counter_tb"])
    with pytest.raises(SystemExit):
        main([str(OPTIONS), "-DINVERT", "--test-modules", "counter_tb"])


def _cocotb_runner_check():
    """Skip unless cocotb has the DigSim runner (not in cocotb 2.1)"""
    if importlib.util.find_spec("cocotb") is None:
        pytest.skip("cocotb isn't installed")
    check = (
        "from cocotb_tools.runner import SUPPORTED_RUNNERS; print('digsim' in SUPPORTED_RUNNERS)"
    )
    run = subprocess.run(
        [sys.executable, "-c", check], check=False, capture_output=True, text=True
    )
    if run.stdout.strip() != "True":
        pytest.skip("cocotb has no DigSim runner")


_RUNNER_SCRIPT = """
import sys
from cocotb_tools.runner import get_runner

build_dir, counter, testbench = sys.argv[1:]
sys.path.insert(0, testbench)
runner = get_runner("digsim")
for _ in range(2):
    runner.build(sources=[counter], hdl_toplevel="counter", build_dir=build_dir)
runner.test(
    test_module="counter_tb",
    hdl_toplevel="counter",
    plusargs=["+digsim_plusarg=42"],
    waves=True,
)
"""


def test_cocotb_runner(tmp_path):
    """cocotb's Python runner: build() synthesizes once, test() runs the tests"""
    _cocotb_runner_check()
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("COCOTB_") and name not in ("WAVES", "PYTEST_CURRENT_TEST")
    }
    command = [sys.executable, "-c", _RUNNER_SCRIPT, str(tmp_path), str(COUNTER), str(TESTBENCH)]
    run = subprocess.run(command, check=False, env=env, capture_output=True, text=True)
    output = run.stdout + run.stderr
    assert run.returncode == 0, output
    assert "Skipping synthesis" in output
    cases = ET.parse(tmp_path / "results.xml").getroot().findall(".//testcase")
    assert len(cases) == 7
    assert [case.get("name") for case in cases if case.find("failure") is not None] == []
    assert (tmp_path / "counter.json").is_file()
    assert len(_changes(tmp_path / "counter.vcd", "clk")) > 20


def test_cocotb_pytest_plugin(tmp_path):
    """cocotb's pytest plugin with --cocotb-simulator=digsim"""
    _cocotb_runner_check()
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("COCOTB_") and name != "PYTEST_CURRENT_TEST"
    }
    command = [sys.executable, "-m", "pytest", "-p", "cocotb_tools._pytest.plugin"]
    command += ["--cocotb-simulator=digsim", "-p", "no:cacheprovider", "-q"]
    command += [str(TESTBENCH / "plugin_counter.py")]
    run = subprocess.run(
        command, check=False, cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "2 passed, 1 passed cocotb runner" in run.stdout
