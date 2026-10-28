# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Test that the netlists of Verilog files are kept, by the file contents"""

import tempfile
from pathlib import Path

import platformdirs
import pytest

import digsim.circuit.components._yosys_component as yosys_component
from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.synth import Synthesis


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


COUNTER = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.v"


@pytest.fixture(autouse=True)
def empty_cache():
    yosys_component._netlist_cache.clear()
    yield
    yosys_component._netlist_cache.clear()


@pytest.fixture(name="synth_count")
def fixture_synth_count(monkeypatch):
    """The number of times Yosys synthesizes"""
    count = [0]
    synth_to_dict = Synthesis.synth_to_dict

    def counting(self, silent=False):
        count[0] += 1
        return synth_to_dict(self, silent)

    monkeypatch.setattr(Synthesis, "synth_to_dict", counting)
    return count


@pytest.fixture(name="work_dir")
def fixture_work_dir():
    """A folder Yosys can read: YoWASP has a private /tmp"""
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        yield Path(work_dir)


def test_same_file_synthesized_once(synth_count):
    first = YosysComponent.synthesize_file(COUNTER)
    second = YosysComponent.synthesize_file(COUNTER)
    assert synth_count[0] == 1
    assert first == second
    # Each call gets a dict of its own
    second["modules"].clear()
    assert YosysComponent.synthesize_file(COUNTER) == first


def test_functional_is_another_netlist(synth_count):
    gates = YosysComponent.synthesize_file(COUNTER)
    functional = YosysComponent.synthesize_file(COUNTER, functional=True)
    assert synth_count[0] == 2
    assert gates != functional
    assert YosysComponent.synthesize_file(COUNTER, functional=True) == functional
    assert synth_count[0] == 2


def test_changed_file_synthesized_again(synth_count, work_dir):
    path = work_dir / "m.v"
    path.write_text("module m(input a, output y); assign y = a; endmodule\n", encoding="utf-8")
    first = YosysComponent.synthesize_file(path)
    path.write_text("module m(input a, output y); assign y = ~a; endmodule\n", encoding="utf-8")
    second = YosysComponent.synthesize_file(path)
    assert synth_count[0] == 2
    assert first != second


def test_not_cached_runs_yosys_and_has_the_log(synth_count):
    YosysComponent.synthesize_file(COUNTER)
    log = []
    YosysComponent.synthesize_file(COUNTER, log=log, cached=False)
    assert synth_count[0] == 2
    assert len(log) > 0
    # The netlist is kept
    YosysComponent.synthesize_file(COUNTER)
    assert synth_count[0] == 2


def test_components_use_the_cache(synth_count):
    circuit = Circuit()
    YosysComponent(circuit, COUNTER)
    YosysComponent(circuit, COUNTER)
    assert synth_count[0] == 1


def test_two_modules(work_dir):
    path = work_dir / "two.v"
    path.write_text("module a; endmodule\nmodule b; endmodule\n", encoding="utf-8")
    with pytest.raises(yosys_component.YosysComponentException):
        YosysComponent.synthesize_file(path)


def test_oldest_netlist_goes_when_full():
    cache = yosys_component._NetlistCache()
    keys = [(f"file{index}.v", "hash", False) for index in range(cache.SIZE + 1)]
    for index, key in enumerate(keys):
        cache.put(key, {"index": index})
        if index == 1:
            # The first one is used, so the second one is the oldest
            assert cache.get(keys[0]) == {"index": 0}
    assert cache.get(keys[0]) == {"index": 0}
    assert cache.get(keys[1]) is None
    assert cache.get(keys[-1]) == {"index": cache.SIZE}


def test_file_changed_during_synthesis_is_not_kept(synth_count, work_dir, monkeypatch):
    """
    The file is saved again while Yosys reads it: the netlist may be of the new text, it
    is not kept under the hash of the old text
    """
    path = work_dir / "m.v"
    first = "module m(input a, output y); assign y = a; endmodule\n"
    path.write_text(first, encoding="utf-8")
    synth_to_dict = Synthesis.synth_to_dict

    def changed_during(self, silent=False):
        result = synth_to_dict(self, silent)
        path.write_text(first.replace("= a", "= ~a"), encoding="utf-8")
        return result

    monkeypatch.setattr(Synthesis, "synth_to_dict", changed_during)
    YosysComponent.synthesize_file(path)
    monkeypatch.undo()
    path.write_text(first, encoding="utf-8")
    count = [0]
    original = Synthesis.synth_to_dict

    def counting(self, silent=False):
        count[0] += 1
        return original(self, silent)

    monkeypatch.setattr(Synthesis, "synth_to_dict", counting)
    YosysComponent.synthesize_file(path)
    # Not in the cache: Yosys runs again
    assert count[0] == 1
