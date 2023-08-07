# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""Helper module for yosys synthesis"""

import subprocess
import tempfile


class SynthesisException(Exception):
    """Exception class for yosys synthesis"""


class Synthesis:
    """Helper class for yosys synthesis"""

    @classmethod
    def list_modules(cls, verilog_files):
        """List available moduels in verilog files"""
        if isinstance(verilog_files, str):
            verilog_files = [verilog_files]
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".ys") as stream:
            stream.write(f"read -sv {' '.join(verilog_files)}\n")
            stream.write("ls\n")
            stream.flush()

            with subprocess.Popen(
                ["yosys", stream.name],
                stdout=subprocess.PIPE,
                stdin=None,
            ) as process:
                modules = []
                ls_output_found = False
                while process.poll() is None:
                    line = process.stdout.readline().decode("utf-8").rstrip()
                    if "modules:" in line:
                        ls_output_found = True
                    if ls_output_found and "$abstract" in line:
                        modules.append(line.replace("$abstract\\", "").strip())
                if process.returncode != 0:
                    raise SynthesisException("Yosys execution failed...")
        return modules

    def __init__(self, verilog_files, json_output_file, verilog_top_module):
        if isinstance(verilog_files, str):
            self._verilog_files = [verilog_files]
        else:
            self._verilog_files = verilog_files
        self._json_output_file = json_output_file
        self._verilog_top_module = verilog_top_module
        self._yosys_log = []

    def execute(self, silent=False):
        """Execute yosys with generated synthesis script"""
        success = False
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".ys") as stream:
            stream.write(f"read -sv {' '.join(self._verilog_files)}\n")
            stream.write(f"hierarchy -top {self._verilog_top_module}\n")
            stream.write("proc; flatten\n")
            stream.write("memory_dff\n")
            stream.write("proc; opt; techmap; opt\n")
            stream.write(f"synth -top {self._verilog_top_module}\n")
            stream.write(f"write_json {self._json_output_file}\n")
            stream.flush()

            with subprocess.Popen(
                ["yosys", stream.name],
                stdout=subprocess.PIPE,
                stdin=None,
            ) as process:
                while process.poll() is None:
                    line = process.stdout.readline().decode("utf-8").rstrip()
                    if len(line) == 0:
                        continue
                    self._yosys_log.append(line)
                    if not silent:
                        print("Yosys: ", line)
                success = process.returncode == 0
        return success

    def get_log(self):
        """Get the yosys output"""
        return self._yosys_log
