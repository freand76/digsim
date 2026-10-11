# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module that handles the creation of vcd files
"""

import io
from typing import Any

from vcd import VCDWriter

from .components.atoms import Port
from .components.atoms._port import connection_generation


class WavesWriter:
    """Class that handles the creation of vcd files"""

    def __init__(self, filename: str) -> None:
        self._vcd_name: str = filename
        self._vcd_file: io.TextIOWrapper | None = None
        self._vcd_writer: VCDWriter | None = None
        self._vcd_dict: dict[Port, Any] = {}
        # Per port: the variables of all ports it drives, valid for one connection generation
        self._vars_cache: dict[Port, list[tuple[Port, Any]]] = {}
        self._vars_cache_generation = -1

    def init(self, ports: list[Port]) -> None:
        """Initialize vcd writer, with a variable for each port"""
        if self._vcd_file is not None or self._vcd_writer is not None:
            self.close()
        self._vcd_file = open(self._vcd_name, mode="w", encoding="utf-8")  # noqa
        if self._vcd_file is None:
            raise RuntimeError("VCD file is None")
        self._vcd_writer = VCDWriter(self._vcd_file, timescale="1 ns", date="today")
        self._vcd_dict = {}
        self._vars_cache = {}
        for port in ports:
            var = self._vcd_writer.register_var(port.path(), port.name(), "wire", size=port.width)
            self._vcd_dict[port] = var
        self._vcd_file.flush()

    def _port_vars(self, port: Port) -> list[tuple[Port, Any]]:
        """The (port, variable) pairs to update when 'port' changes"""
        if self._vars_cache_generation != connection_generation.value:
            self._vars_cache = {}
            self._vars_cache_generation = connection_generation.value
        port_vars = self._vars_cache.get(port)
        if port_vars is None:
            port_vars = []
            for wired_port in port.get_wired_ports_recursive():
                var = self._vcd_dict.get(wired_port)
                if var is not None:
                    port_vars.append((wired_port, var))
            self._vars_cache[port] = port_vars
        return port_vars

    def write(self, port: Port, time_ns: int) -> None:
        """Write port value to vcd file"""
        if self._vcd_file is None:
            raise RuntimeError("VCD file is None")
        if self._vcd_writer is None:
            raise RuntimeError("VCD Writer is None")
        change = self._vcd_writer.change
        for wired_port, var in self._port_vars(port):
            change(var, timestamp=time_ns, value=wired_port.value)

    def flush(self) -> None:
        """Write buffered changes to the vcd file"""
        if self._vcd_file is not None:
            self._vcd_file.flush()

    def close(self) -> None:
        """Close vcd file"""
        if self._vcd_writer is not None:
            self._vcd_writer.close()
            self._vcd_writer = None

        if self._vcd_file is not None:
            self._vcd_file.close()
            self._vcd_file = None

        self._vcd_dict = {}
        self._vars_cache = {}
