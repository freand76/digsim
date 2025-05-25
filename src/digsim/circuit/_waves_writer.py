# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the creation of vcd files
"""

import io
from typing import Any, Tuple

from vcd import VCDWriter

from .components.atoms import Port


class WavesWriter:
    """Class that handles the creation of vcd files"""

    def __init__(self, filename: str):
        self._vcd_name: str = filename
        self._vcd_file: io.TextIOWrapper | None = None
        self._vcd_writer: VCDWriter | None = None
        self._vcd_dict: dict[str, Any] = {}

    def init(self, port_info: list[Tuple[str, str, int]]):
        """Initialize vcd writer"""
        if self._vcd_file is not None or self._vcd_writer is not None:
            self.close()
        self._vcd_file = open(self._vcd_name, mode="w", encoding="utf-8")
        if self._vcd_file is None:
            raise RuntimeError("VCD file is None")
        self._vcd_writer = VCDWriter(self._vcd_file, timescale="1 ns", date="today")
        for port_path, port_name, port_width in port_info:
            var = self._vcd_writer.register_var(port_path, port_name, "wire", size=port_width)
            self._vcd_dict[f"{port_path}.{port_name}"] = var
        self._vcd_file.flush()

    def write(self, port: Port, time_ns: int):
        """Write port value to vcd file"""
        if self._vcd_file is None:
            raise RuntimeError("VCD file is None")
        if self._vcd_writer is None:
            raise RuntimeError("VCD Writer is None")
        for wired_port in port.get_wired_ports_recursive():
            var = self._vcd_dict.get(f"{wired_port.path()}.{wired_port.name()}")
            if var is None:
                continue
            self._vcd_writer.change(var, timestamp=time_ns, value=wired_port.value)
        self._vcd_file.flush()

    def close(self):
        """Close vcd file"""
        if self._vcd_writer is not None:
            self._vcd_writer.close()
            self._vcd_writer = None

        if self._vcd_file is not None:
            self._vcd_file.close()
            self._vcd_file = None

        self._vcd_dict = {}
