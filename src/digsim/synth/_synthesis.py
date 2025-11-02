# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Helper module for yosys synthesis"""

import json
import pathlib
import shutil
import site
import sys

import pexpect
import pexpect.popen_spawn

from digsim.circuit.components.atoms import DigsimException


class SynthesisException(DigsimException):
    """Exception class for yosys synthesis"""


class Synthesis:
    """Helper class for yosys synthesis"""

    @classmethod
    def _pexpect_wait_for_prompt(cls, pexp):
        index = pexp.expect(["yosys>", pexpect.EOF])
        before_lines = pexp.before.decode("utf8").replace("\r", "").split("\n")
        if index == 0:
            pass
        elif index == 1:
            # Unexpected EOF means ERROR
            errorline = "ERROR"
            for line in before_lines:
                if "ERROR" in line:
                    errorline = line
                    break
            raise SynthesisException(errorline)

        # Remove escape sequence in output
        out_lines = []
        for line in before_lines:
            if line.startswith("\x1b"):
                continue
            out_lines.append(line)
        return out_lines

    @staticmethod
    def _find_win_yowasp_yosys_binary():
        try:
            # Use getusersitepackages if this is present, as it ensures that the
            # value is initialised properly.
            user_site = site.getusersitepackages()
        except AttributeError:
            user_site = site.USER_SITE
        scripts_path = pathlib.Path(user_site).parent / "Scripts"
        yowasp_yosys_path = scripts_path / "yowasp-yosys.exe"
        if yowasp_yosys_path.is_file():
            return str(yowasp_yosys_path)
        return None

    @classmethod
    def _pexpect_spawn_yosys(cls):
        # Find linux binary
        yosys_exe = shutil.which("yosys") or shutil.which("yowasp-yosys")

        # No binary found
        if yosys_exe is None:
            # Try to find windows binary
            yosys_exe = cls._find_win_yowasp_yosys_binary()

        if yosys_exe is None:
            raise SynthesisException("Yosys executable not found")

        if sys.platform == "win32":
            return pexpect.popen_spawn.PopenSpawn(yosys_exe)

        return pexpect.spawn(yosys_exe)

    @classmethod
    def list_modules(cls, verilog_files):
        """List available modules in verilog files"""
        if isinstance(verilog_files, str):
            verilog_files = [verilog_files]

        pexp = cls._pexpect_spawn_yosys()
        cls._pexpect_wait_for_prompt(pexp)
        pexp.sendline(f"read -sv {' '.join(verilog_files)}")
        cls._pexpect_wait_for_prompt(pexp)
        pexp.sendline("ls")
        pexp.expect("\n")
        ls_response = cls._pexpect_wait_for_prompt(pexp)
        pexp.sendline("exit")

        modules = []
        for line in ls_response:
            if len(line) == 0:
                continue
            if "modules:" in line:
                continue
            modules.append(line.replace("$abstract\\", "").strip())
        return modules

    def __init__(self, verilog_files, verilog_top_module):
        if isinstance(verilog_files, str):
            self._verilog_files = [verilog_files]
        else:
            self._verilog_files = verilog_files
        self._verilog_top_module = verilog_top_module
        self._yosys_log = []

    def synth_to_json(self, silent=False):
        """Execute yosys with generated synthesis script"""
        script = f"read -sv {' '.join(self._verilog_files)}; "
        script += f"hierarchy -top {self._verilog_top_module}; "
        script += "proc; flatten; "
        script += "memory_dff; "
        script += "proc; opt; techmap; opt; "
        script += f"synth -noabc -top {self._verilog_top_module}; "

        pexp = self._pexpect_spawn_yosys()
        self._pexpect_wait_for_prompt(pexp)
        pexp.sendline(script)
        yosys_log = self._pexpect_wait_for_prompt(pexp)
        for line in yosys_log:
            self._yosys_log.append(line)
            if silent:
                continue
            print("Yosys:", line)
        pexp.sendline("write_json")
        pexp.expect("Executing JSON backend.")
        json_lines = self._pexpect_wait_for_prompt(pexp)
        pexp.sendline("exit")

        return "\n".join(json_lines)

    def synth_to_dict(self, silent=False):
        """Execute yosys with generated synthesis script and return python dict"""
        yosys_json = self.synth_to_json(silent)
        try:
            netlist_dict = json.loads(yosys_json)
        except json.JSONDecodeError as exc:
            raise SynthesisException(f"Malformed JSON output from Yosys: {exc}") from exc
        return netlist_dict

    def synth_to_json_file(self, filename, silent=False):
        """Execute yosys with generated synthesis script and write to file"""
        yosys_json = self.synth_to_json(silent)
        if yosys_json is None:
            raise SynthesisException("Yosys synthesis failed")
        with open(filename, mode="w", encoding="utf-8") as json_file:
            json_file.write(yosys_json)

    def get_log(self):
        """Get the yosys output"""
        return self._yosys_log
