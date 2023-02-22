# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" The main class module of the digsim.synth namespace """

import argparse
import sys
import time

from . import Synthesis


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Yosys synthesizer helper")
    parser.add_argument(
        "--input-files", "-i", type=str, nargs="*", required=True, help="The verilog input files"
    )
    parser.add_argument(
        "--output-file", "-o", type=str, required=True, help="The json output file"
    )
    parser.add_argument("--top", "-t", type=str, required=True, help="The verilog top module")
    parser.add_argument("--silent", "-s", action="store_true", help="Silent the yosys output")
    args = parser.parse_args()
    print("Synthesis started...")
    for infile in args.input_files:
        print(f" - Reading {infile}")
    print(f"Generating {args.output_file}...")
    start_time = time.monotonic()
    synthesis = Synthesis(args.input_files, args.output_file, args.top)
    returncode = synthesis.execute(silent=args.silent)
    if returncode:
        print(f"Synthesis complete in {time.monotonic() - start_time:.2f}s")
    else:
        print("ERROR: Synthesis failed!")
        sys.exit(-1)
