# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Helper module for yosys synthesis"""

import json
import shutil

import pexpect
from digsim.circuit.components.atoms import DigsimException


class SynthesisException(DigsimException):
    """Exception class for yosys synthesis"""


class Synthesis:
    """Helper class for yosys synthesis"""

    @classmethod
    def _yosys_exe(cls):
        _yosys_exe = shutil.which("yowasp-yosys")
        if _yosys_exe is None:
            raise SynthesisException("Yosys executable not found")
        return _yosys_exe

    @classmethod
    def list_modules(cls, verilog_files):
        """List available modules in verilog files"""
        if isinstance(verilog_files, str):
            verilog_files = [verilog_files]

        pexp = pexpect.spawn(cls._yosys_exe())
        pexp.expect("yosys>")
        pexp.sendline(f"read -sv {' '.join(verilog_files)}")
        pexp.expect("yosys>")
        pexp.sendline("ls")
        pexp.expect("\n")
        pexp.expect("yosys>")
        ls_response = pexp.before.decode("utf-8").replace("\r", "").split("\n")
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
        script += f"synth -top {self._verilog_top_module}; "

        pexp = pexpect.spawn(self._yosys_exe())
        pexp.expect("yosys>")
        pexp.sendline(script)
        yosys_log = pexp.before.decode("utf-8").replace("\r", "").split("\n")
        for line in yosys_log:
            self._yosys_log.append(line)
            if silent:
                continue
            print("Yosys:", line)

        pexp.expect("yosys>")
        pexp.sendline("write_json")
        pexp.expect("Executing JSON backend.")
        pexp.expect("yosys>")
        yosys_json = pexp.before.decode("utf-8")
        pexp.sendline("exit")

        return yosys_json

    def synth_to_dict(self, silent=False):
        """Execute yosys with generated synthesis script and return python dict"""
        yosys_json = self.synth_to_json(silent)
        netlist_dict = json.loads(yosys_json)
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
