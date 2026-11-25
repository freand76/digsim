# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The launcher: it synthesizes the design (or loads its netlist), builds the circuit, puts
the stand-in for `cocotb.simulator` in place before cocotb is imported, starts cocotb like
the GPI does, and runs the simulation. With --netlist it only synthesizes, the build step
of cocotb's runner.
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
from digsim.circuit.components._yosys_component import top_module
from digsim.synth import Synthesis, SynthesisException
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


def _define(text: str) -> tuple[str, str | None]:
    """A macro: NAME or NAME=VALUE"""
    name, _, value = text.partition("=")
    return name, value if "=" in text else None


# A sized Verilog constant, like 8'd5 or 4'b1010
_SIZED_CONSTANT = re.compile(r"\d*'s?([bodh])([0-9a-f_]+)", re.IGNORECASE)
_BASES = {"b": 2, "o": 8, "d": 10, "h": 16}


def _parameter(text: str) -> tuple[str, int]:
    """
    A parameter: NAME=VALUE, the value an integer (like 8, 0x10 or 8'd5)

    Raises:
        argparse.ArgumentTypeError: If it has no value, or the value isn't an integer.
    """
    name, equals, value = text.partition("=")
    if not equals:
        raise argparse.ArgumentTypeError(f"'{text}' is not NAME=VALUE")
    value = value.strip()
    try:
        return name, int(value, 0)
    except ValueError:
        pass
    match = _SIZED_CONSTANT.fullmatch(value)
    if match is None:
        raise argparse.ArgumentTypeError(f"The value of parameter '{name}' is not an integer")
    return name, int(match.group(2).replace("_", ""), _BASES[match.group(1).lower()])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m digsim.cocotb",
        description=(
            "Run cocotb tests on a Verilog design, synthesized with Yosys, or only "
            "synthesize it with --netlist. Plusargs (+name=value) are for the tests."
        ),
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="The Verilog files, or a netlist (.json) written with --netlist",
    )
    parser.add_argument(
        "--toplevel", default=os.environ.get("COCOTB_TOPLEVEL"), help="The top module"
    )
    parser.add_argument(
        "--test-modules",
        default=os.environ.get("COCOTB_TEST_MODULES"),
        help="The Python modules with the tests, separated by commas",
    )
    parser.add_argument(
        "-I",
        dest="includes",
        metavar="FOLDER",
        action="append",
        default=[],
        help="A folder to include files from",
    )
    parser.add_argument(
        "-D",
        dest="defines",
        metavar="NAME[=VALUE]",
        action="append",
        default=[],
        type=_define,
        help="A macro, like `define",
    )
    parser.add_argument(
        "-P",
        dest="parameters",
        metavar="NAME=VALUE",
        action="append",
        default=[],
        type=_parameter,
        help="A value for a parameter of the top module, an integer",
    )
    parser.add_argument(
        "--functional", action="store_true", help="Synthesize into functional blocks"
    )
    parser.add_argument(
        "--netlist",
        metavar="FILE",
        help="Only synthesize: write the netlist to FILE, to run the tests on later",
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
    return parser


def _synthesis(
    parser: argparse.ArgumentParser, args: argparse.Namespace, toplevel: str | None
) -> Synthesis:
    """The synthesis of the Verilog files, with the time declarations removed"""
    sources = [_yosys_source(source) for source in args.sources]
    includes = list(args.includes)
    # A copy without the time declarations includes files from the folder of the original
    for source, used in zip(args.sources, sources, strict=True):
        folder = str(Path(source).resolve().parent)
        if used != str(Path(source).resolve()) and not re.search(r"[\s\";#]", folder):
            includes.append(folder)
    if toplevel is None:
        if len(sources) > 1 or args.includes or args.defines:
            parser.error("Give --toplevel or set COCOTB_TOPLEVEL")
        toplevel = top_module(sources[0])
    return Synthesis(
        sources,
        toplevel,
        functional=args.functional,
        parameters=dict(args.parameters),
        includes=includes,
        defines=dict(args.defines),
    )


def _design(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    toplevel: str | None,
    circuit: Circuit,
) -> YosysComponent:
    """The design as a component of the circuit, from a netlist or the Verilog files"""
    # The named signals (wires and registers), for the tests and the waves
    signals = not args.no_signals
    if len(args.sources) == 1 and args.sources[0].endswith(".json"):
        if args.includes or args.defines or args.parameters or args.functional:
            parser.error("A netlist is used as it is: no -I, -D, -P or --functional")
        return YosysComponent(circuit, args.sources[0], signals=signals)
    netlist = _synthesis(parser, args, toplevel).synth_to_dict(silent=True)
    top = YosysComponent(circuit, signals=signals)
    top.create_from_netlist(YosysNetlist(**netlist))
    return top


def _run(parser: argparse.ArgumentParser, args: argparse.Namespace, plusargs: list[str]) -> int:
    # The Makefiles can give the library with the module, like "top.counter"
    toplevel = args.toplevel.strip().rsplit(".", 1)[-1] if args.toplevel else None
    if args.netlist:
        if not args.netlist.endswith(".json"):
            parser.error("The netlist is a .json file")
        netlist = _synthesis(parser, args, toplevel).synth_to_json(silent=True)
        Path(args.netlist).write_text(netlist, encoding="utf-8")
        return 0
    if not args.test_modules:
        parser.error("Give --test-modules or set COCOTB_TEST_MODULES")
    os.environ["COCOTB_TEST_MODULES"] = args.test_modules
    if args.toplevel:
        os.environ["COCOTB_TOPLEVEL"] = args.toplevel
    # The test modules are found in the current folder, like with the Makefiles
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    circuit = Circuit()
    top = _design(parser, args, toplevel, circuit)
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


def main(argv: list[str] | None = None) -> int:
    """Run cocotb's tests on a Verilog design, or synthesize it (see --help)"""
    parser = _parser()
    arguments = sys.argv[1:] if argv is None else argv
    # Plusargs (+name or +name=value) are for the tests, like with other simulators. Taken
    # out first: argparse would take them for sources.
    plusargs = [arg for arg in arguments if arg.startswith("+")]
    args = parser.parse_args([arg for arg in arguments if not arg.startswith("+")])
    try:
        return _run(parser, args, plusargs)
    except SynthesisException as error:
        for line in error.log:
            print("Yosys:", line, file=sys.stderr)
        print(f"DigSim: {error}", file=sys.stderr)
        return 1
