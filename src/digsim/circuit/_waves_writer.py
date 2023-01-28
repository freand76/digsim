# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Module that handles the creation of vcd files
"""

# pylint: disable=consider-using-with
# pylint: disable=import-error

from vcd import VCDWriter


class WavesWriter:
    """Class that handles the creation of vcd files"""

    def __init__(self, filename):
        self._vcd_name = filename
        self._vcd_file = None
        self._vcd_writer = None
        self._vcd_dict = {}

    def init(self, port_info):
        """Initialize vcd writer"""
        if self._vcd_file is not None or self._vcd_writer is not None:
            self.close()
        self._vcd_file = open(self._vcd_name, mode="w", encoding="utf-8")
        self._vcd_writer = VCDWriter(self._vcd_file, timescale="1 ns", date="today")
        for port_path, port_name, port_width in port_info:
            var = self._vcd_writer.register_var(port_path, port_name, "wire", size=port_width)
            self._vcd_dict[f"{port_path}.{port_name}"] = var

    def write(self, port, time_ns):
        """Write port value to vcd file"""
        var = self._vcd_dict.get(f"{port.path()}.{port.name()}")
        if var is None:
            return
        self._vcd_writer.change(var, timestamp=time_ns, value=port.value)
        for wire in port.get_wires():
            self.write(wire, time_ns)

    def close(self):
        """Close vcd file"""
        if self._vcd_writer is not None:
            self._vcd_writer.close()
            self._vcd_writer = None

        if self._vcd_file is not None:
            self._vcd_file.close()
            self._vcd_file = None

        self._vcd_dict = {}
