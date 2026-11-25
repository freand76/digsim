# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The launcher: it builds the circuit, puts the stand-in for `cocotb.simulator` in place
before cocotb is imported, starts cocotb like the GPI does, and runs the simulation
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import os
import re
import sys
import types
from pathlib import Path

import platformdirs

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist

from . import _simulator


# SystemVerilog time declarations in a module, which Yosys can't parse. DigSim has a time
# of its own, so they don't matter.
_TIME_DECLARATION = re.compile(r"\btime(unit|precision)\b[^;]*;")


class _SimulatorFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Imports `cocotb.simulator` from digsim.cocotb._simulator"""

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname != "cocotb.simulator":
            return None
        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        for name in _simulator.__all__:
            setattr(module, name, getattr(_simulator, name))


def _yosys_source(source: str) -> str:
    """The source, or a copy in the cache without the time declarations that Yosys rejects"""
    path = Path(source).resolve()
    text = path.read_text(encoding="utf-8")
    stripped = _TIME_DECLARATION.sub("", text)
    if stripped == text:
        return str(path)
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:16]
    folder = Path(platformdirs.user_cache_dir("digsim", appauthor=False)) / "cocotb" / digest
    folder.mkdir(parents=True, exist_ok=True)
    copy = folder / path.name
    copy.write_text(stripped, encoding="utf-8")
    return str(copy)


def main(argv: list[str] | None = None) -> int:
    """Run cocotb's tests on a Verilog design"""
    parser = argparse.ArgumentParser(
        prog="python -m digsim.cocotb", description="Run cocotb tests on a Verilog design"
    )
    parser.add_argument("sources", nargs="+", help="The Verilog files")
    parser.add_argument(
        "--toplevel", default=os.environ.get("COCOTB_TOPLEVEL"), help="The top module"
    )
    parser.add_argument(
        "--test-modules",
        default=os.environ.get("COCOTB_TEST_MODULES"),
        help="The Python modules with the tests, separated by commas",
    )
    parser.add_argument(
        "--functional", action="store_true", help="Synthesize into functional blocks"
    )
    parser.add_argument(
        "--waves",
        metavar="FILE",
        help="Write the waveforms to a VCD file, with the named signals inside the design",
    )
    parser.add_argument(
        "--no-signals",
        action="store_true",
        help="Leave out the named signals inside the design, for a faster simulation",
    )
    args, extra = parser.parse_known_args(argv)
    # Plusargs (+name or +name=value) are for the tests, like with other simulators
    plusargs = [arg for arg in extra if arg.startswith("+")]
    if len(plusargs) != len(extra):
        parser.error(f"unrecognized arguments: {' '.join(set(extra) - set(plusargs))}")
    # The Makefiles can give the library with the module, like "top.counter"
    toplevel = args.toplevel.strip().rsplit(".", 1)[-1] if args.toplevel else None
    if len(args.sources) > 1 and not toplevel:
        parser.error("Give --toplevel or set COCOTB_TOPLEVEL with several Verilog files")
    if not args.test_modules:
        parser.error("Give --test-modules or set COCOTB_TEST_MODULES")
    os.environ["COCOTB_TEST_MODULES"] = args.test_modules
    if args.toplevel:
        os.environ["COCOTB_TOPLEVEL"] = args.toplevel
    # The test modules are found in the current folder, like with the Makefiles
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    sources = [_yosys_source(source) for source in args.sources]
    # The named signals (wires and registers), for the tests and the waves
    signals = not args.no_signals
    circuit = Circuit()
    if len(sources) == 1:
        top = YosysComponent(
            circuit, sources[0], functional=args.functional, signals=signals, module=toplevel
        )
    else:
        assert toplevel is not None
        netlist = Synthesis(sources, toplevel, functional=args.functional).synth_to_dict(
            silent=True
        )
        top = YosysComponent(circuit, signals=signals)
        top.create_from_netlist(YosysNetlist(**netlist))
    scheduler = _simulator._Scheduler(
        circuit, top, str(Path(args.sources[0]).resolve()), [parser.prog, *plusargs]
    )
    if args.waves:
        circuit.vcd(args.waves, timescale=_simulator.TIMESCALE)
    _simulator.install(scheduler)
    if "cocotb" in sys.modules:
        raise RuntimeError("cocotb was imported before the DigSim simulator was installed")
    sys.meta_path.insert(0, _SimulatorFinder())

    # What the GPI does at the start of the simulation
    from pygpi.entry import load_entry

    try:
        load_entry()
        scheduler.run()
    finally:
        circuit.vcd_close()
    return 0
