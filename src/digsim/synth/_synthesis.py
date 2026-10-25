# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Helper module for yosys synthesis"""

from __future__ import annotations

import gc
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal

import platformdirs
import yowasp_yosys

from digsim.circuit.components.atoms import DigsimException


VerilogFiles = str | os.PathLike[str] | Sequence[str | os.PathLike[str]]

# The parameters of the top module that a synthesis changes, by name
Parameters = Mapping[str, int]

# One Yosys at a time: it sends the console output of the whole process to a file, and the
# GUI synthesizes in a thread
_yosys_lock = threading.Lock()


def _file_list(verilog_files: VerilogFiles) -> list[str]:
    if isinstance(verilog_files, (str, os.PathLike)):
        return [str(verilog_files)]
    return [str(verilog_file) for verilog_file in verilog_files]


# Folders that the WebAssembly Yosys (YoWASP) has of its own, which hide the real ones
_YOWASP_FOLDERS = ("tmp", "share")


def _yosys_path(path: pathlib.Path) -> tuple[pathlib.Path | None, str]:
    """
    The path that Yosys reads a file by, or None and why it can't read it.

    The WebAssembly Yosys (YoWASP) sees the folders of the file system root (the drives on
    Windows) and, by relative paths, the working folder, but not files directly in the
    root, not the real /tmp and /share by absolute paths (it has its own), and it doesn't
    follow links to absolute paths. A path with links in it is
    given as its real path, which also finds a file in /tmp on macOS (/private/tmp).
    """
    absolute = pathlib.Path(os.path.abspath(path))
    if os.name == "nt":
        # Not the real path: that is a network path for a network drive letter
        if not absolute.drive.endswith(":"):
            return None, (
                "network paths can't be read by the WebAssembly Yosys (YoWASP), "
                "use a drive letter for the network folder"
            )
        return path, ""
    real = path.resolve()
    if real == absolute:
        if not path.is_absolute():
            # YoWASP sees the working folder and its parents by relative paths, in any
            # folder
            return path, ""
        # Kept as it is, Yosys writes it into the netlist
        yosys_path = path
    else:
        yosys_path = real
    parts = real.parts
    if len(parts) < 3:
        return None, "files directly in / can't be read by the WebAssembly Yosys (YoWASP)"
    if parts[1] in _YOWASP_FOLDERS:
        return None, (
            f"the WebAssembly Yosys (YoWASP) has a /{parts[1]} folder of its own, "
            f"which hides the files in /{parts[1]}"
        )
    return yosys_path, ""


def yosys_path_problem(path: str | os.PathLike[str]) -> str | None:
    """
    Why the Yosys of DigSim can't read a file, None if it can. The WebAssembly Yosys
    (YoWASP) can't read files in /tmp on Linux, in /share, or directly in /, and not
    network paths on Windows.

    Args:
        path: The path of a Verilog file.
    """
    yosys_path, problem = _yosys_path(pathlib.Path(path))
    return problem if yosys_path is None else None


def _parameter_value(value: int) -> str:
    """A parameter value as a Verilog constant for Yosys, which can't read a minus sign"""
    if value >= 0:
        return str(value)
    width = max(32, (-value - 1).bit_length() + 1)
    return f"{width}'sb{value & ((1 << width) - 1):0{width}b}"


def _parameter_arguments(parameters: Parameters | None) -> str:
    """
    The parameters as arguments of the Yosys command hierarchy (-chparam).

    Raises:
        SynthesisException: If a name is not a Verilog identifier, or a value not an int.
    """
    arguments = ""
    for name, value in (parameters or {}).items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
            raise SynthesisException(f"Not a parameter name: '{name}'")
        if not isinstance(value, int):
            raise SynthesisException(f"The value of parameter '{name}' is not an integer")
        arguments += f" -chparam {name} {_parameter_value(int(value))}"
    return arguments


def _rtlil_value(text: str) -> int | str:
    """A constant of an RTLIL file as a number: 4, 8'00000100 or 8's11111100 (signed)"""
    if text.lstrip("-").isdigit():
        return int(text)
    match = re.fullmatch(r"(\d+)'(s?)([01]+)", text)
    if match is None:
        return text
    width, signed, bits = int(match.group(1)), match.group(2), match.group(3)
    value = int(bits, 2)
    if signed and bits[0] == "1":
        value -= 1 << width
    return value


def _script_path(path: pathlib.Path) -> str:
    """A path for a Yosys script: forward slashes, quoted in case it contains spaces"""
    return f'"{path.as_posix()}"'


def _script_files(verilog_files: VerilogFiles) -> str:
    """
    The verilog files as arguments in a Yosys script

    Raises:
        SynthesisException: If Yosys can't read a file, see yosys_path_problem.
    """
    paths = []
    for file in _file_list(verilog_files):
        path, problem = _yosys_path(pathlib.Path(file))
        if path is None:
            raise SynthesisException(
                f"Yosys can't read {file}: {problem}. Move the file to another folder."
            )
        paths.append(_script_path(path))
    return " ".join(paths)


@contextmanager
def _console_to_file(console_file: pathlib.Path) -> Iterator[None]:
    """
    Send this process's console output (file descriptors 1 and 2) to a file.
    The WebAssembly Yosys runs in this process and writes warnings and errors directly
    to the console, also with '-qq'. They are in the log file as well, but the console
    output is kept for errors that happen before the log file is opened.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    # Opened first: if that fails, no saved file descriptors are left open
    console = os.open(console_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    saved = [os.dup(1), os.dup(2)]
    try:
        os.dup2(console, 1)
        os.dup2(console, 2)
        yield
    finally:
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        for fd in (*saved, console):
            os.close(fd)


@dataclass(frozen=True)
class YosysMessage:
    """
    An error or a warning in the Yosys log.

    Args:
        kind: "error" or "warning".
        text: The message, without the file, line and kind.
        file: The file the message is about, None if it doesn't say.
        line: The line in the file, from 1, None if it doesn't say.
    """

    kind: Literal["error", "warning"]
    text: str
    file: str | None = None
    line: int | None = None


# "/path/file.v:3: ERROR: syntax error", "file.v:2.5-2.9: Warning: ...", "ERROR: ..."
_MESSAGE = re.compile(
    r"^(?:(?P<file>.+?):(?P<line>\d+)(?:\.\d+(?:-\d+\.\d+)?)?: )?"
    r"(?P<kind>ERROR|Warning): (?P<text>.*)$"
)


def parse_messages(log: Sequence[str]) -> list[YosysMessage]:
    """The errors and warnings in a Yosys log, each once, in the order of the log"""
    messages: list[YosysMessage] = []
    for log_line in log:
        match = _MESSAGE.match(log_line.strip())
        if match is None:
            continue
        line = match.group("line")
        message = YosysMessage(
            kind="error" if match.group("kind") == "ERROR" else "warning",
            text=match.group("text"),
            file=match.group("file"),
            line=int(line) if line is not None else None,
        )
        if message not in messages:
            messages.append(message)
    return messages


class SynthesisException(DigsimException):
    """
    Yosys could not synthesize the Verilog, the message is the Yosys error.

    Attributes:
        log: The Yosys log, empty if Yosys didn't write one.
        messages: The errors and warnings in the log, see parse_messages(). An error
            that isn't in the log is the only message.
    """

    def __init__(self, message: str, log: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.log = list(log)
        self.messages = parse_messages(self.log)
        if not any(message.kind == "error" for message in self.messages):
            self.messages.append(YosysMessage("error", message.removeprefix("ERROR: ")))


class Synthesis:
    """
    Synthesizes Verilog into a netlist with Yosys, which a YosysComponent can be built from.

    Args:
        verilog_files: One Verilog file, or a list of them.
        verilog_top_module: The name of the module to synthesize.
        functional: Synthesize into functional blocks, like adders, multiplexers and
            registers, instead of gates and one-bit flip-flops. The netlist has far fewer
            cells, so it simulates faster.
        parameters: Values for parameters of the top module, by name, instead of their
            defaults, like {"WIDTH": 16}. The values are integers.

    Raises:
        SynthesisException: If a parameter name is not a Verilog identifier, or its value
            not an integer. A parameter that the module doesn't have is an error of the
            synthesis.
    """

    @staticmethod
    @contextmanager
    def _work_dir() -> Iterator[pathlib.Path]:
        """
        A temporary folder for the files written by Yosys.
        It is created in the user cache folder, not the system temp folder: the
        WebAssembly Yosys (YoWASP) maps '/tmp' to a private folder of its own.
        """
        cache_dir = pathlib.Path(platformdirs.user_cache_dir("digsim", appauthor=False))
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Cleanup errors are ignored: on Windows a file still open by Yosys cannot be deleted
        with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
            yield pathlib.Path(work_dir)

    @staticmethod
    def _run_yosys(script: str, work_dir: pathlib.Path, log: list[str]) -> None:
        """
        Run a Yosys script with the WebAssembly Yosys (YoWASP) in this process. The
        Yosys log is added to 'log'.
        """
        log_file = work_dir / "yosys.log"
        console_file = work_dir / "console.txt"
        # Everything Yosys writes goes to the log file. The WebAssembly Yosys only
        # understands absolute paths with forward slashes, also on Windows (C:/...).
        args = ["-qq", "-l", log_file.as_posix(), "-p", script]
        with _yosys_lock, _console_to_file(console_file):
            returncode = yowasp_yosys.run_yosys(args)
        if returncode != 0:
            # When Yosys fails, the WebAssembly instance is kept alive by a reference
            # cycle (in yowasp-runtime) and keeps its files open; on Windows the
            # work folder can then not be removed. Collect it to close the files.
            gc.collect()
        if log_file.exists():
            log.extend(log_file.read_text(encoding="utf-8").splitlines())
        if returncode != 0:
            error = next((line for line in log if "ERROR" in line), None)
            if error is None:
                # No error in the log, for example if the log file could not be written
                output = console_file.read_text(encoding="utf-8", errors="replace").strip()
                error = f"Yosys failed with exit code {returncode}"
                if output:
                    error += ": " + " ".join(output.splitlines()[-3:])
            raise SynthesisException(error, log)

    @classmethod
    def list_modules(cls, verilog_files: VerilogFiles, log: list[str] | None = None) -> list[str]:
        """
        The names of the modules in Verilog files.

        Args:
            verilog_files: One Verilog file, or a list of them.
            log: A list to add the Yosys log to.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error.
        """
        files = _script_files(verilog_files)
        with cls._work_dir() as work_dir:
            modules_file = work_dir / "modules.txt"
            script = f"read -sv {files}; tee -q -o {_script_path(modules_file)} ls"
            cls._run_yosys(script, work_dir, log if log is not None else [])
            ls_response = modules_file.read_text(encoding="utf-8").splitlines()

        modules = []
        for line in ls_response:
            if len(line.strip()) == 0:
                continue
            if "modules:" in line:
                continue
            modules.append(line.replace("$abstract\\", "").strip())
        return modules

    @classmethod
    def list_parameters(
        cls, verilog_files: VerilogFiles, module: str, log: list[str] | None = None
    ) -> dict[str, int | str]:
        """
        The parameters of a module and their defaults, in the order of the Verilog. A
        default is an integer, or text if it isn't one (like a string parameter).

        Args:
            verilog_files: One Verilog file, or a list of them.
            module: The name of the module.
            log: A list to add the Yosys log to.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error, or the
                files have no such module.
        """
        yosys_log = log if log is not None else []
        modules = cls.list_module_parameters(verilog_files, yosys_log)
        if module not in modules:
            raise SynthesisException(f"ERROR: No module '{module}'", yosys_log)
        return modules[module]

    @classmethod
    def list_module_parameters(
        cls, verilog_files: VerilogFiles, log: list[str] | None = None
    ) -> dict[str, dict[str, int | str]]:
        """
        The parameters of every module in Verilog files and their defaults, by module, see
        list_parameters(). A module without parameters has an empty dict.

        Args:
            verilog_files: One Verilog file, or a list of them.
            log: A list to add the Yosys log to.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error.
        """
        files = _script_files(verilog_files)
        with cls._work_dir() as work_dir:
            rtlil_file = work_dir / "modules.il"
            script = f"read_verilog -sv {files}; write_rtlil {_script_path(rtlil_file)}"
            cls._run_yosys(script, work_dir, log if log is not None else [])
            rtlil = rtlil_file.read_text(encoding="utf-8").splitlines()
        modules: dict[str, dict[str, int | str]] = {}
        parameters: dict[str, int | str] = {}
        for line in rtlil:
            if line.startswith("module "):
                parameters = modules.setdefault(line.split()[1].removeprefix("\\"), {})
            elif line.startswith("  parameter "):
                # A module's own parameter (the ones of its cells are indented more):
                # "parameter [signed] \NAME [value]"
                words = line.split()[1:]
                if words[0] == "signed":
                    words = words[1:]
                value = " ".join(words[1:])
                parameters[words[0].removeprefix("\\")] = _rtlil_value(value)
        return modules

    def __init__(
        self,
        verilog_files: VerilogFiles,
        verilog_top_module: str,
        functional: bool = False,
        parameters: Parameters | None = None,
    ) -> None:
        self._verilog_files = _file_list(verilog_files)
        self._verilog_top_module = verilog_top_module
        self._functional = functional
        self._parameter_arguments = _parameter_arguments(parameters)
        self._yosys_log: list[str] = []

    def synth_to_json(self, silent: bool = False) -> str:
        """
        Synthesize, and return the netlist as JSON text.

        Args:
            silent: Don't print the Yosys log.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error.
        """
        top = self._verilog_top_module
        script = f"read -sv {_script_files(self._verilog_files)}; "
        script += f"hierarchy -top {top}{self._parameter_arguments}; "
        # Tristate buffers ('bz) become tristate cells: several on one net are merged into
        # one, and the ones that don't drive an output port of the design become logic
        script += "proc; flatten; tribuf -merge -logic; "
        if self._functional:
            # The coarse synthesis only, without mapping to gates. Without alumacc, an
            # adder stays an $add cell instead of an $alu, and the memories are mapped to
            # registers and multiplexers. Without the FSM passes, a state machine keeps
            # its encoding, and the names of its states (see YosysComponent signals).
            script += f"synth -noabc -noalumacc -nofsm -top {top} -run begin:fine; "
            script += "memory_map; opt -full; clean; "
        else:
            script += "memory_dff; "
            script += "proc; opt; techmap; opt; "
            script += f"synth -noabc -top {top}; "

        self._yosys_log = []
        with self._work_dir() as work_dir:
            json_file = work_dir / "netlist.json"
            try:
                self._run_yosys(
                    script + f"write_json {_script_path(json_file)}", work_dir, self._yosys_log
                )
            finally:
                if not silent:
                    for line in self._yosys_log:
                        print("Yosys:", line)
            return json_file.read_text(encoding="utf-8")

    def synth_to_dict(self, silent: bool = False) -> dict[str, Any]:
        """
        Synthesize, and return the netlist as a dict, for YosysNetlist(**netlist_dict).

        Args:
            silent: Don't print the Yosys log.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error.
        """
        yosys_json = self.synth_to_json(silent)
        try:
            netlist_dict = json.loads(yosys_json)
        except json.JSONDecodeError as exc:
            raise SynthesisException(f"Malformed JSON output from Yosys: {exc}") from exc
        return netlist_dict

    def synth_to_json_file(self, filename: str | pathlib.Path, silent: bool = False) -> None:
        """
        Synthesize, and write the netlist to a JSON file.

        Args:
            filename: The netlist file to write.
            silent: Don't print the Yosys log.

        Raises:
            SynthesisException: If Yosys reports an error, like a syntax error.
        """
        yosys_json = self.synth_to_json(silent)
        with open(filename, mode="w", encoding="utf-8") as json_file:
            json_file.write(yosys_json)

    def get_log(self) -> list[str]:
        """The Yosys log of the last synthesis"""
        return self._yosys_log

    def get_messages(self) -> list[YosysMessage]:
        """The errors and warnings of the last synthesis, see parse_messages()"""
        return parse_messages(self._yosys_log)
