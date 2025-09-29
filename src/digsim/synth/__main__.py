# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main class module of the digsim.synth namespace"""

import argparse
import sys
import time

from . import Synthesis, SynthesisException


def _synth_modules(args):
    print("Synthesis started...")
    for infile in args.input_files:
        print(f" - Reading {infile}")
    print(f"Generating {args.output_file}...")
    start_time = time.monotonic()
    synthesis = Synthesis(args.input_files, args.top)
    try:
        synthesis.synth_to_json_file(args.output_file, silent=args.silent)
        print(f"Synthesis complete in {time.monotonic() - start_time:.2f}s")
    except SynthesisException as exc:
        print(f"ERROR: {str(exc)}")
        return -1
    return 0


def _list_modules(args):
    try:
        modules = Synthesis.list_modules(args.input_files)
        print("Modules:")
        print("========")
        for idx, module in enumerate(modules):
            print(f"{idx}: {module}")
        print("========")
    except SynthesisException as exc:
        print(f"ERROR: {str(exc)}")
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
    synth_parser.set_defaults(func=_synth_modules)
    list_parser = subparser.add_parser("list")
    list_parser.add_argument(
        "--input-files", "-i", type=str, nargs="+", required=True, help="The verilog input files"
    )
    list_parser.set_defaults(func=_list_modules)
    arguments = parser.parse_args()
    returncode = arguments.func(arguments)
    sys.exit(returncode)
