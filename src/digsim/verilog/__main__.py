# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Format Verilog files: python -m digsim.verilog format file.v"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import VerilogFormatError, VerilogFormatter


def _read(name: str) -> str:
    if name == "-":
        return sys.stdin.read()
    # newline="" keeps \r\n, the formatter writes the newlines it reads
    with open(name, encoding="utf-8", newline="") as file:
        return file.read()


def _format(args: argparse.Namespace) -> int:
    formatter = VerilogFormatter(indent=args.indent, blank_lines=args.blank_lines)
    returncode = 0
    for name in args.files:
        try:
            text = _read(name)
            formatted = formatter.format(text)
        except (OSError, UnicodeDecodeError, VerilogFormatError) as exc:
            print(f"ERROR: {name}: {exc}", file=sys.stderr)
            returncode = 2
            continue
        if args.check:
            if formatted != text:
                print(f"Would format {name}")
                returncode = max(returncode, 1)
        elif args.in_place and name != "-":
            if formatted != text:
                Path(name).write_text(formatted, encoding="utf-8", newline="")
                print(f"Formatted {name}")
        else:
            sys.stdout.write(formatted)
    return returncode


def main(argv: list[str] | None = None) -> int:
    """The command line tool, returns the exit code"""
    parser = argparse.ArgumentParser(prog="python -m digsim.verilog", description="Verilog tools")
    subparser = parser.add_subparsers(required=True)
    format_parser = subparser.add_parser(
        "format",
        help="Format Verilog files",
        description="Format Verilog files: the indentation and the whitespace around lines. "
        "Exit code 1 if --check finds files to format, 2 if a file can't be formatted.",
    )
    format_parser.add_argument("files", nargs="+", help="The Verilog files, - for stdin")
    mode = format_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--in-place", "-i", action="store_true", help="Write the formatted files back"
    )
    mode.add_argument(
        "--check", action="store_true", help="Only list the files that would be formatted"
    )
    format_parser.add_argument(
        "--indent", type=int, default=4, help="Spaces per indentation step (default 4)"
    )
    format_parser.add_argument(
        "--blank-lines", type=int, default=1, help="The most empty lines in a row (default 1)"
    )
    format_parser.set_defaults(func=_format)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
