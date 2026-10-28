# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test the steps of synthesizing a Verilog file in the editor"""

import tempfile
import threading
from pathlib import Path

import platformdirs
import pytest

import digsim.circuit.components._yosys_component as yosys_component
from digsim.app._build_flow import run_synthesis
from digsim.circuit.components import YosysComponent, YosysVariant
from digsim.synth import Synthesis


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


VERILOG = Path(__file__).parent / "verilog"
GATES, FUNCTIONAL = YosysVariant(False), YosysVariant(True)


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


def _run(path, variants):
    steps = []
    result = run_synthesis(path, variants, steps.append)
    return result, [(step.name, step.status, step.detail) for step in steps], steps


def test_steps(monkeypatch):
    yosys_component._netlist_cache.clear()
    result, steps, raw = _run(VERILOG / "one_module.v", {FUNCTIONAL, GATES})
    assert steps == [
        ("List modules", "running", ""),
        ("List modules", "ok", "Module module_one"),
        ("Synthesize into gates", "running", ""),
        ("Synthesize into gates", "ok", ""),
        ("Synthesize into functional blocks", "running", ""),
        ("Synthesize into functional blocks", "ok", ""),
    ]
    assert all(step.seconds is not None for step in raw if step.status != "running")
    assert set(result.netlists) == {GATES, FUNCTIONAL}
    assert len(result.log) > 0
    assert result.messages == []
    # The components get the netlists without running Yosys again
    monkeypatch.setattr(Synthesis, "synth_to_dict", None)
    assert YosysComponent.synthesize_file(VERILOG / "one_module.v") == result.netlists[GATES]


def test_syntax_error():
    result, steps, _ = _run(VERILOG / "syntax_error.v", {GATES})
    assert steps[-1][:2] == ("List modules", "error")
    assert steps[-1][2].startswith("Line 4: syntax error")
    assert result.netlists is None
    (error,) = result.errors()
    assert error.line == 4


def test_error_in_synthesis():
    """module_with_error.v reads, but has a port that is not declared"""
    result, steps, _ = _run(VERILOG / "module_with_error.v", {GATES})
    assert [step[:2] for step in steps][-1] in (
        ("List modules", "error"),
        ("Synthesize into gates", "error"),
    )
    assert result.netlists is None
    assert result.errors()


def test_two_modules():
    result, steps, _ = _run(VERILOG / "multiple_modules.v", {GATES})
    assert steps[-1] == (
        "List modules",
        "error",
        "The file has 3 modules, a Yosys component needs one",
    )
    assert result.netlists is None
    assert result.errors()[0].text == "The file has 3 modules, a Yosys component needs one"


def test_warnings():
    result, steps, _ = _run(VERILOG / "module_with_warning.v", {GATES})
    name, status, detail = steps[-1]
    assert (name, status) == ("Synthesize into gates", "warning")
    assert detail.endswith(" warnings")
    assert result.netlists is not None
    assert len(result.warnings()) >= 2
    assert result.errors() == []


def test_missing_file(work_dir):
    result, steps, _ = _run(work_dir / "missing.v", {GATES})
    assert steps[-1][:2] == ("List modules", "error")
    assert result.netlists is None
    assert result.errors()


def test_yosys_in_two_threads():
    """One Yosys runs at a time, both get their netlists"""
    results = {}

    def synthesize(functional):
        results[functional] = YosysComponent.synthesize_file(
            VERILOG / "functional_regs.v", functional, cached=False
        )

    threads = [threading.Thread(target=synthesize, args=(variant,)) for variant in (False, True)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results[False] != results[True]
    assert results[False] == YosysComponent.synthesize_file(VERILOG / "functional_regs.v")
