# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
RAM and ROM components, with a configurable size, clocked or asynchronous, and contents
loaded from a file
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from .atoms import (
    VALUE_TYPE,
    Component,
    ComponentException,
    Parameter,
    ParameterValue,
    PortIn,
    PortOutDelta,
    PortWire,
)


if TYPE_CHECKING:
    from digsim.circuit import Circuit

MAX_ADDRESS_WIDTH = 20
MAX_DATA_WIDTH = 32

# Text files in the format of Verilog's $readmemh, other files are binary
TEXT_FILE_TYPES = (".hex", ".mem", ".txt")

_FILEINFO = "Memory contents (*.bin *.hex *.mem *.txt);;All files (*)"

_COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)


def _read_text(path: Path, data_width: int, load_address: int) -> dict[int, int]:
    """
    The words of a text file like Verilog's $readmemh reads: hexadecimal words separated
    by whitespace, with // and /* */ comments, and @address to continue at an address
    """
    text = _COMMENTS.sub(" ", path.read_text(encoding="utf-8"))
    if text.lstrip().startswith(":"):
        raise ComponentException(f"{path.name}: Intel HEX files are not supported")
    words: dict[int, int] = {}
    address = load_address
    for token in text.split():
        try:
            if token.startswith("@"):
                address = load_address + int(token[1:].replace("_", ""), 16)
                continue
            value = int(token.replace("_", ""), 16)
        except ValueError:
            raise ComponentException(f"{path.name}: '{token}' is not a hexadecimal number")
        if value >= 1 << data_width:
            raise ComponentException(
                f"{path.name}: {token} does not fit in a word of {data_width} bits"
            )
        words[address] = value
        address += 1
    return words


def _read_binary(path: Path, data_width: int, load_address: int) -> dict[int, int]:
    """The words of a binary file, little-endian when a word has more than one byte"""
    data = path.read_bytes()
    word_bytes = (data_width + 7) // 8
    if len(data) % word_bytes != 0:
        raise ComponentException(
            f"{path.name}: {len(data)} bytes is not a whole number of {word_bytes} byte words"
        )
    words: dict[int, int] = {}
    for index in range(len(data) // word_bytes):
        word = data[index * word_bytes : (index + 1) * word_bytes]
        value = int.from_bytes(word, "little")
        if value >= 1 << data_width:
            raise ComponentException(
                f"{path.name}: {value:#x} at address {load_address + index:#x} does not fit "
                f"in a word of {data_width} bits, a binary file has {word_bytes} bytes per word"
            )
        words[load_address + index] = value
    return words


def read_memory_file(
    path: str | Path, address_width: int, data_width: int, load_address: int = 0
) -> dict[int, int]:
    """
    Read the contents of a memory from a file, as a dict from address to word.

    A file ending in .hex, .mem or .txt is text, read like Verilog's $readmemh. Other files
    are binary, with the bytes of each word in little-endian order.
    """
    file_path = Path(path)
    try:
        if file_path.suffix.lower() in TEXT_FILE_TYPES:
            words = _read_text(file_path, data_width, load_address)
        else:
            words = _read_binary(file_path, data_width, load_address)
    except (OSError, UnicodeDecodeError) as exc:
        raise ComponentException(f"Could not read {file_path.name}: {exc}") from exc
    size = 1 << address_width
    outside = [address for address in words if not 0 <= address < size]
    if outside:
        raise ComponentException(
            f"{file_path.name} does not fit in the memory: address {max(outside):#x} "
            f"is outside of its {size} words"
        )
    return words


class _Memory(Component):
    """The base class of RAM and ROM"""

    _MODES: tuple[str, ...] = ()
    _WRITABLE = False

    def __init__(
        self,
        circuit: Circuit,
        name: str | None,
        address_width: int,
        data_width: int,
        mode: str,
        edge: str,
        output_enable: bool,
        path: str | Path | None,
        load_address: int,
        byte_enable: bool = False,
    ) -> None:
        super().__init__(circuit, name)
        if not 1 <= address_width <= MAX_ADDRESS_WIDTH:
            raise ComponentException(f"The address width must be 1 to {MAX_ADDRESS_WIDTH}")
        if not 1 <= data_width <= MAX_DATA_WIDTH:
            raise ComponentException(f"The data width must be 1 to {MAX_DATA_WIDTH}")
        if mode not in self._MODES:
            raise ComponentException(f"Unknown mode '{mode}', use one of {list(self._MODES)}")
        if edge not in ("rising", "falling"):
            raise ComponentException(f"Unknown edge '{edge}', use 'rising' or 'falling'")
        path = str(path) if path else None
        self._size = 1 << address_width
        self._preload = (
            read_memory_file(path, address_width, data_width, load_address) if path else {}
        )
        self._mem: list[VALUE_TYPE] = [0] * self._size
        self._clocked = mode != "async"
        self._sync_read = mode == "sync"
        self._rising = edge == "rising"
        self._output_enable = output_enable
        self._byte_enable = byte_enable
        # The value read on the last clock edge (sync), and the value on DataOut (async)
        self._read_value: VALUE_TYPE = "X"
        self._driven: VALUE_TYPE = "X"
        self.parameter_set("address_width", address_width)
        self.parameter_set("data_width", data_width)
        self.parameter_set("mode", mode)
        self.parameter_set("edge", edge)
        self.parameter_set("output_enable", output_enable)
        self.parameter_set("path", path)
        self.parameter_set("load_address", load_address)
        if self._WRITABLE:
            self.parameter_set("byte_enable", byte_enable)

        # With a synchronous read, only the clock (and OE) update the memory
        input_class = PortWire if self._sync_read else PortIn
        if self._clocked:
            self.add_port(PortIn(self, "clk"))
        self.add_port(input_class(self, "Address", width=address_width))
        if self._WRITABLE:
            self.add_port(input_class(self, "DataIn", width=data_width))
            self.add_port(input_class(self, "WE"))
            if byte_enable:
                self.add_port(input_class(self, "BE", width=(data_width + 7) // 8))
        if output_enable:
            self.add_port(PortIn(self, "OE"))
        data_out = PortOutDelta(self, "DataOut", width=data_width)
        data_out.set_tristate(output_enable)
        self.add_port(data_out)

    def init(self) -> None:
        super().init()
        # A reset starts over with the contents of the file
        self._mem = [0] * self._size
        for address, value in self._preload.items():
            self._mem[address] = value

    def default_state(self) -> None:
        self._read_value = "X"
        self._driven = "X"

    def _edge(self) -> bool:
        if self._rising:
            return self.clk.is_rising_edge()
        return self.clk.is_falling_edge()

    def _write(self) -> None:
        """Write DataIn to the address, while WE is 1"""

    def _drive(self, value: VALUE_TYPE) -> None:
        """Drive DataOut with value, or "Z" while it is not enabled"""
        if self._output_enable:
            enable = self.OE.value
            if enable == 0:
                value = "Z"
            elif enable != 1:
                value = "X"
        if value != self._driven:
            self._driven = value
            self.DataOut.value = value

    def _word(self) -> VALUE_TYPE:
        """The word at the address, "X" when the address is undefined"""
        address = self.Address.value
        return self._mem[address] if isinstance(address, int) else "X"

    def update(self) -> None:
        if self._sync_read:
            if self._edge() and isinstance(self.Address.value, int):
                if self._WRITABLE and self.WE.value == 1:
                    # A write leaves DataOut as it is
                    self._write()
                else:
                    self._read_value = self._word()
                    if not self._output_enable:
                        # Driven on every read, also with the same value
                        self.DataOut.value = self._read_value
                        return
            if self._output_enable:
                self._drive(self._read_value)
            return
        # Without a clock, a RAM writes while WE is 1
        write = self._edge() if self._clocked else True
        if self._WRITABLE and write:
            self._write()
        self._drive(self._word())

    def reload_contents(self) -> None:
        """
        Read the file again, after it changed: the memory has its contents when the
        circuit is initialized or reset.
        """
        path = self.parameter_get("path")
        self._preload = (
            read_memory_file(
                path,
                self.parameter_get("address_width"),
                self.parameter_get("data_width"),
                self.parameter_get("load_address"),
            )
            if path
            else {}
        )

    def read(self, address: int) -> VALUE_TYPE:
        """
        Return the word at an address.

        Args:
            address: The address.
        """
        return self._mem[address]

    def settings_to_dict(self) -> dict[str, ParameterValue]:
        settings = super().settings_to_dict()
        if settings["path"]:
            settings["path"] = self.circuit.store_path(str(settings["path"]))
        else:
            # Only a file is loaded from a path, see ComponentDataClass.create()
            del settings["path"]
        return settings

    @classmethod
    def _memory_parameters(cls, modes: dict[str, str]) -> dict[str, Parameter]:
        return {
            "address_width": {
                "type": "int",
                "min": 1,
                "max": MAX_ADDRESS_WIDTH,
                "default": 8,
                "description": "Address width (the memory has 2^width words)",
            },
            "data_width": {
                "type": "int",
                "min": 1,
                "max": MAX_DATA_WIDTH,
                "default": 8,
                "description": "Data width (bits in a word)",
            },
            "mode": {
                "type": "list",
                "items": list(modes),
                "default": next(iter(modes)),
                "description": "Mode: " + ", ".join(f"{k} ({v})" for k, v in modes.items()),
            },
            "edge": {
                "type": "list",
                "items": ["rising", "falling"],
                "default": "rising",
                "description": "Clock edge (with a clock)",
            },
            "output_enable": {
                "type": "bool",
                "default": False,
                "description": "Output enable input (DataOut is not driven while OE is 0)",
            },
        }


class RAM(_Memory):
    """
    A RAM with 2^`address_width` words of `data_width` bits. It starts out with zeros, or
    with the contents of a file, and is filled again from the file when the circuit is
    initialized or reset.

    The mode sets how the RAM is clocked:

    - "sync": DataIn is written, while WE is 1, or DataOut read, while WE is 0, on the
      clock edge. A write leaves DataOut as it is. Like the block RAM of an FPGA.
    - "async_read": DataIn is written on the clock edge while WE is 1, DataOut is the
      word at the address at all times.
    - "async": no clock. DataIn is written while WE is 1, DataOut is the word at the
      address at all times. Like an asynchronous SRAM.

    With `byte_enable`, a write only changes the bytes of the word that BE selects, like
    the byte strobes of a processor's store: bit 0 of BE is bits 7:0 of the word, bit 1
    bits 15:8 and so on.

    The file is binary, with the bytes of each word in little-endian order, or text (.hex,
    .mem or .txt) with hexadecimal words like Verilog's $readmemh reads, also with
    @address lines.

    Ports:
        clk: Clock input, not in "async" mode.
        Address: Input, `address_width` bits.
        DataIn: Input, `data_width` bits.
        WE: Write enable input.
        BE: Byte enable input, with `byte_enable`, one bit for each byte of a word (8 bits
            of `data_width`, rounded up).
        OE: Output enable input, with `output_enable`. DataOut is "Z" while it is 0.
        DataOut: Output, `data_width` bits. Tristate with `output_enable`.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        address_width: The number of address bits, 1 to 20.
        data_width: The number of bits in a word, 1 to 32.
        mode: "sync", "async_read" or "async", see above.
        edge: The clock edge, "rising" or "falling".
        output_enable: Add an output enable input.
        path: A file with the contents to load, optional.
        load_address: The address to load the file at.
        byte_enable: Add a byte enable input, see above.
    """

    _MODES = ("sync", "async_read", "async")
    _WRITABLE = True

    def __init__(
        self,
        circuit: Circuit,
        name: str | None = None,
        address_width: int = 8,
        data_width: int = 8,
        mode: str = "sync",
        edge: str = "rising",
        output_enable: bool = False,
        path: str | Path | None = None,
        load_address: int = 0,
        byte_enable: bool = False,
    ) -> None:
        super().__init__(
            circuit,
            name,
            address_width,
            data_width,
            mode,
            edge,
            output_enable,
            path,
            load_address,
            byte_enable,
        )

    def _write(self) -> None:
        address = self.Address.value
        if self.WE.value == 1 and isinstance(address, int):
            value = self.DataIn.value
            if self._byte_enable:
                value = self._merge_bytes(self._mem[address], value, self.BE.value)
            self._mem[address] = value

    def _merge_bytes(self, old: VALUE_TYPE, new: VALUE_TYPE, enable: VALUE_TYPE) -> VALUE_TYPE:
        """The word after a write of the bytes that enable selects"""
        all_bytes = (1 << self.BE.width) - 1
        if enable == all_bytes:
            return new
        if enable == 0:
            return old
        if not (isinstance(old, int) and isinstance(new, int) and isinstance(enable, int)):
            return "X"
        mask = sum(0xFF << (8 * byte) for byte in range(self.BE.width) if enable >> byte & 1)
        return (old & ~mask | new & mask) & ((1 << self.DataIn.width) - 1)

    def write(self, address: int, value: VALUE_TYPE) -> None:
        """
        Write a word to an address, like a testbench preparing the memory. Call it after
        Circuit.init(), which fills the memory again from its file.

        Args:
            address: The address.
            value: The word.
        """
        self._mem[address] = value
        if not self._sync_read:
            self._drive(self._word())

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            **cls._memory_parameters(
                {
                    "sync": "clocked",
                    "async_read": "clocked write",
                    "async": "no clock",
                }
            ),
            "byte_enable": {
                "type": "bool",
                "default": False,
                "description": "Byte enable input (a write only changes the bytes BE selects)",
            },
            "path": {
                "type": "path",
                "fileinfo": _FILEINFO,
                "default": "",
                "description": "Contents from a file (optional)",
            },
        }


class ROM(_Memory):
    """
    A ROM with 2^`address_width` words of `data_width` bits, with the contents of a file.
    The words that the file doesn't fill are zero.

    The mode sets how the ROM is read:

    - "async": no clock, DataOut is the word at the address at all times.
    - "sync": DataOut is read on the clock edge.

    The file is binary, with the bytes of each word in little-endian order, or text (.hex,
    .mem or .txt) with hexadecimal words like Verilog's $readmemh reads, also with
    @address lines.

    Ports:
        clk: Clock input, in "sync" mode.
        Address: Input, `address_width` bits.
        OE: Output enable input, with `output_enable`. DataOut is "Z" while it is 0.
        DataOut: Output, `data_width` bits. Tristate with `output_enable`.

    Args:
        circuit: The circuit to add the component to.
        path: The file with the contents.
        name: The component name, the class name if not given.
        address_width: The number of address bits, 1 to 20.
        data_width: The number of bits in a word, 1 to 32.
        mode: "async" or "sync", see above.
        edge: The clock edge, "rising" or "falling".
        output_enable: Add an output enable input.
        load_address: The address to load the file at.
    """

    _MODES = ("async", "sync")

    def __init__(
        self,
        circuit: Circuit,
        path: str | Path,
        name: str | None = None,
        address_width: int = 8,
        data_width: int = 8,
        mode: str = "async",
        edge: str = "rising",
        output_enable: bool = False,
        load_address: int = 0,
    ) -> None:
        if not path:
            raise ComponentException("A ROM needs a file with its contents")
        super().__init__(
            circuit,
            name,
            address_width,
            data_width,
            mode,
            edge,
            output_enable,
            path,
            load_address,
        )

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "path": {
                "type": "path",
                "fileinfo": _FILEINFO,
                "description": "Open the file with the contents of the ROM",
            },
            **cls._memory_parameters({"async": "no clock", "sync": "clocked"}),
        }
