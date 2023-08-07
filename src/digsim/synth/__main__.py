# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" The main class module of the digsim.synth namespace """

import argparse
import sys
import time

from . import Synthesis


def _synth_modules(args):
    print("Synthesis started...")
    for infile in args.input_files:
        print(f" - Reading {infile}")
    print(f"Generating {args.output_file}...")
    start_time = time.monotonic()
    synthesis = Synthesis(args.input_files, args.output_file, args.top)
    return_value = synthesis.execute(silent=args.silent)
    if return_value:
        print(f"Synthesis complete in {time.monotonic() - start_time:.2f}s")
    else:
        print("ERROR: Synthesis failed!")
        return -1
    return 0


def _list_modules(args):
    modules = Synthesis.list_modules(args.input_files)
    print("Modules:")
    print("========")
    for idx, module in enumerate(modules):
        print(f"{idx}: {module}")
    print("========")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Yosys synthesizer helper")
    subparser = parser.add_subparsers()
    synth_parser = subparser.add_parser("synth")
    synth_parser.add_argument(
        "--input-files", "-i", type=str, nargs="*", required=True, help="The verilog input files"
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
        "--input-files", "-i", type=str, nargs="*", required=True, help="The verilog input files"
    )
    list_parser.set_defaults(func=_list_modules)
    arguments = parser.parse_args()
    returncode = arguments.func(arguments)
    sys.exit(returncode)
