# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Formatted Verilog synthesizes to the same netlist as the Verilog before formatting"""

import re
import tempfile
from pathlib import Path

import platformdirs
import pytest

from digsim.synth import Synthesis
from digsim.verilog import VerilogFormatter


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


ROOT = Path(__file__).parent.parent
# One module in each file
VERILOG_FILES = [
    ROOT / "examples" / "pytest_tb" / "alu.v",
    ROOT / "examples" / "pytest_tb" / "up_down_counter.v",
    ROOT / "examples" / "yosys_counter" / "counter.v",
    ROOT / "examples" / "yosys_fsm" / "traffic_light.sv",
    ROOT / "tests" / "verilog" / "functional_comb.v",
    ROOT / "tests" / "verilog" / "functional_regs.v",
    ROOT / "tests" / "verilog" / "tristate.v",
]


# The file and line in the names that Yosys makes, like "$add$/path/counter.v:14$2"
_FILE_LINE = re.compile(r"\$[^$]*\.s?v:\d+\$")


def _without_src(value):
    """
    The netlist without the 'src' attributes and the file and line in names: they change
    with the file and the empty lines
    """
    if isinstance(value, dict):
        return {
            _without_src(key): _without_src(item) for key, item in value.items() if key != "src"
        }
    if isinstance(value, list):
        return [_without_src(item) for item in value]
    if isinstance(value, str):
        return _FILE_LINE.sub("$FILE$", value)
    return value


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


@pytest.mark.parametrize("path", VERILOG_FILES, ids=lambda path: path.name)
def test_same_netlist(path, work_dir):
    formatted = work_dir / path.name
    formatted.write_text(
        VerilogFormatter(indent=2).format(path.read_text(encoding="utf-8")), encoding="utf-8"
    )
    top = Synthesis.list_modules(path)[0]
    before = Synthesis(path, top).synth_to_dict(silent=True)
    after = Synthesis(formatted, top).synth_to_dict(silent=True)
    assert _without_src(after) == _without_src(before)
