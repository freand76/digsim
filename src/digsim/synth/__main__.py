# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The main class module of the digsim.synth namespace"""

import argparse
import sys
import time

from . import Synthesis, SynthesisException


def _parameter(text: str) -> tuple[str, int]:
    """A parameter of the command line, NAME=VALUE"""
    name, equals, value = text.partition("=")
    try:
        if not equals:
            raise ValueError
        return name.strip(), int(value.strip(), 0)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{text}' is not NAME=VALUE with an integer value"
        ) from None


def _synth_modules(args: argparse.Namespace) -> int:
    print("Synthesis started...")
    for infile in args.input_files:
        print(f" - Reading {infile}")
    parameters = dict(args.parameters)
    for name, value in parameters.items():
        print(f" - Parameter {name} = {value}")
    print(f"Generating {args.output_file}...")
    start_time = time.monotonic()
    try:
        synthesis = Synthesis(
            args.input_files, args.top, functional=args.functional, parameters=parameters
        )
        synthesis.synth_to_json_file(args.output_file, silent=args.silent)
        print(f"Synthesis complete in {time.monotonic() - start_time:.2f}s")
    except SynthesisException as exc:
        # The Yosys error message starts with "ERROR:" itself
        print(exc)
        return -1
    except OSError as exc:
        # The output file could not be written
        print(f"ERROR: {exc!s}")
        return -1
    return 0


def _list_modules(args: argparse.Namespace) -> int:
    try:
        modules = Synthesis.list_modules(args.input_files)
        parameters = Synthesis.list_module_parameters(args.input_files)
        print("Modules:")
        print("========")
        for idx, module in enumerate(modules):
            print(f"{idx}: {module}")
            # As synth -p takes them
            for name, value in parameters.get(module, {}).items():
                print(f"   {name} = {value}")
        print("========")
    except SynthesisException as exc:
        print(exc)
        return -1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Yosys synthesizer helper")
    subparser = parser.add_subparsers(required=True)
    synth_parser = subparser.add_parser("synth")
    synth_parser.add_argument(
        "--input-files", "-i", type=str, nargs="+", required=True, help="The verilog input files"
    )
    synth_parser.add_argument(
        "--output-file", "-o", type=str, required=True, help="The json output file"
    )
    synth_parser.add_argument(
        "--top", "-t", type=str, required=True, help="The verilog top module"
    )
    synth_parser.add_argument(
        "--silent", "-s", action="store_true", help="Silent the yosys output"
    )
    synth_parser.add_argument(
        "--functional",
        "-f",
        action="store_true",
        help="Synthesize into functional blocks (adders, multiplexers, registers) instead of "
        "gates, which simulates faster",
    )
    synth_parser.add_argument(
        "--parameters",
        "-p",
        type=_parameter,
        nargs="+",
        action="extend",
        default=[],
        metavar="NAME=VALUE",
        help="Values for parameters of the top module, like WIDTH=16 (integers: 16, -1, 0xff)",
    )
    synth_parser.set_defaults(func=_synth_modules)
    list_parser = subparser.add_parser("list")
    list_parser.add_argument(
        "--input-files", "-i", type=str, nargs="+", required=True, help="The verilog input files"
    )
    list_parser.set_defaults(func=_list_modules)
    arguments = parser.parse_args()
    returncode = arguments.func(arguments)
    sys.exit(returncode)
