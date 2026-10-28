# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""Pytest module to test the memory components"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import RAM, ROM, MemStdOut
from digsim.circuit.components.atoms import ComponentException


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


def _clock(circuit, memory):
    memory.clk.value = 1
    circuit.run(ms=1)
    memory.clk.value = 0
    circuit.run(ms=1)


def _port_names(component):
    return [port.name() for port in component.ports]


def _ram(circuit, **settings):
    ram = RAM(circuit, **settings)
    circuit.init()
    if "clk" in _port_names(ram):
        ram.clk.value = 0
    ram.WE.value = 0
    return ram


def _write(circuit, ram, address, value):
    ram.Address.value = address
    ram.DataIn.value = value
    ram.WE.value = 1
    _clock(circuit, ram)
    ram.WE.value = 0


def test_ram_sync_write_read():
    """A sync RAM is written and read on the rising clock edge"""
    circuit = Circuit()
    ram = _ram(circuit)
    _write(circuit, ram, 0x12, 0xAB)
    ram.Address.value = 0x12
    circuit.run(ms=1)
    assert ram.DataOut.value == "X"
    _clock(circuit, ram)
    assert ram.DataOut.value == 0xAB
    assert ram.read(0x12) == 0xAB


def test_ram_sync_write_keeps_data_out():
    """A write leaves DataOut with the word read before"""
    circuit = Circuit()
    ram = _ram(circuit)
    ram.write(5, 7)
    ram.Address.value = 5
    _clock(circuit, ram)
    _write(circuit, ram, 5, 9)
    assert ram.DataOut.value == 7
    _clock(circuit, ram)
    assert ram.DataOut.value == 9


def test_ram_falling_edge():
    """With edge="falling", the RAM is written and read on the falling edge"""
    circuit = Circuit()
    ram = _ram(circuit, edge="falling")
    ram.write(3, 0x55)
    ram.Address.value = 3
    ram.clk.value = 1
    circuit.run(ms=1)
    assert ram.DataOut.value == "X"
    ram.clk.value = 0
    circuit.run(ms=1)
    assert ram.DataOut.value == 0x55


def test_ram_async_read():
    """With an async read, DataOut follows the address and the writes on the clock edge"""
    circuit = Circuit()
    ram = _ram(circuit, mode="async_read")
    ram.write(1, 0x11)
    ram.Address.value = 1
    circuit.run(ms=1)
    assert ram.DataOut.value == 0x11
    ram.Address.value = 2
    circuit.run(ms=1)
    assert ram.DataOut.value == 0
    ram.DataIn.value = 0x22
    ram.WE.value = 1
    circuit.run(ms=1)
    # Not written before the clock edge
    assert ram.DataOut.value == 0
    _clock(circuit, ram)
    assert ram.DataOut.value == 0x22


def test_ram_async():
    """Without a clock, the RAM is written while WE is 1"""
    circuit = Circuit()
    ram = _ram(circuit, mode="async", address_width=4, data_width=4)
    assert "clk" not in _port_names(ram)
    ram.Address.value = 3
    ram.DataIn.value = 0xC
    circuit.run(ms=1)
    assert ram.DataOut.value == 0
    ram.WE.value = 1
    circuit.run(ms=1)
    assert ram.DataOut.value == 0xC
    ram.WE.value = 0
    ram.DataIn.value = 0x1
    circuit.run(ms=1)
    assert ram.DataOut.value == 0xC
    ram.Address.value = "X"
    circuit.run(ms=1)
    assert ram.DataOut.value == "X"


def test_ram_output_enable():
    """With an output enable, DataOut is "Z" while OE is 0 and "X" while it is undefined"""
    circuit = Circuit()
    ram = _ram(circuit, mode="async_read", output_enable=True)
    assert ram.DataOut.is_tristate()
    ram.write(0, 0x42)
    ram.Address.value = 0
    ram.OE.value = 0
    circuit.run(ms=1)
    assert ram.DataOut.value == "Z"
    ram.OE.value = 1
    circuit.run(ms=1)
    assert ram.DataOut.value == 0x42
    ram.OE.value = "X"
    circuit.run(ms=1)
    assert ram.DataOut.value == "X"


def test_ram_sync_output_enable():
    """A sync RAM drives the word read on the last clock edge while OE is 1"""
    circuit = Circuit()
    ram = _ram(circuit, output_enable=True)
    ram.write(4, 0x44)
    ram.Address.value = 4
    ram.OE.value = 0
    _clock(circuit, ram)
    assert ram.DataOut.value == "Z"
    ram.OE.value = 1
    circuit.run(ms=1)
    assert ram.DataOut.value == 0x44


def test_ram_preload_binary(tmp_path):
    """A binary file is loaded at the load address, little-endian words"""
    data = tmp_path / "data.bin"
    data.write_bytes(bytes([0x34, 0x12, 0xCD, 0xAB]))
    circuit = Circuit()
    ram = _ram(circuit, data_width=16, path=data, load_address=0x10)
    assert [ram.read(address) for address in (0x0F, 0x10, 0x11, 0x12)] == [0, 0x1234, 0xABCD, 0]


def test_ram_preload_text(tmp_path):
    """A text file has hexadecimal words, comments and @address lines"""
    data = tmp_path / "data.hex"
    data.write_text("// header\n01 0_2 /* skip\n ff */ 03\n@20\nA b\n")
    circuit = Circuit()
    ram = _ram(circuit, path=data)
    assert [ram.read(address) for address in range(4)] == [1, 2, 3, 0]
    assert [ram.read(address) for address in (0x20, 0x21)] == [0xA, 0xB]


def test_ram_init_reloads_file(tmp_path):
    """Circuit.init() fills the RAM again from its file"""
    data = tmp_path / "data.hex"
    data.write_text("5A\n")
    circuit = Circuit()
    ram = _ram(circuit, path=data)
    _write(circuit, ram, 0, 0x99)
    _write(circuit, ram, 1, 0x98)
    assert ram.read(0) == 0x99
    circuit.init()
    assert (ram.read(0), ram.read(1)) == (0x5A, 0)


@pytest.mark.parametrize(
    ("name", "contents", "settings", "error"),
    [
        ("big.bin", bytes(5), {"address_width": 2}, "does not fit in the memory"),
        ("odd.bin", bytes(3), {"data_width": 16}, "whole number"),
        ("wide.hex", "100\n", {}, "does not fit in a word"),
        ("bad.hex", "12 zz\n", {}, "not a hexadecimal number"),
        ("intel.hex", ":0100000000FF\n", {}, "Intel HEX"),
        ("missing.bin", None, {}, "Could not read"),
    ],
)
def test_ram_preload_errors(tmp_path, name, contents, settings, error):
    """A file that doesn't fit or can't be read gives an error that says why"""
    path = tmp_path / name
    if isinstance(contents, bytes):
        path.write_bytes(contents)
    elif contents is not None:
        path.write_text(contents)
    with pytest.raises(ComponentException, match=error):
        RAM(Circuit(), path=path, **settings)


@pytest.mark.parametrize(
    "settings",
    [{"address_width": 0}, {"data_width": 33}, {"mode": "fast"}, {"edge": "both"}],
)
def test_ram_invalid_settings(settings):
    """Settings outside of their range give an error"""
    with pytest.raises(ComponentException):
        RAM(Circuit(), **settings)


def test_rom_async(tmp_path):
    """An async ROM drives the word at the address"""
    data = tmp_path / "rom.bin"
    data.write_bytes(bytes([7, 8, 9]))
    circuit = Circuit()
    rom = ROM(circuit, data, address_width=2)
    circuit.init()
    assert sorted(_port_names(rom)) == ["Address", "DataOut"]
    rom.Address.value = 2
    circuit.run(ms=1)
    assert rom.DataOut.value == 9
    rom.Address.value = 3
    circuit.run(ms=1)
    assert rom.DataOut.value == 0


def test_rom_sync(tmp_path):
    """A sync ROM reads on the clock edge"""
    data = tmp_path / "rom.mem"
    data.write_text("@1 3c\n")
    circuit = Circuit()
    rom = ROM(circuit, data, mode="sync", output_enable=True)
    circuit.init()
    rom.clk.value = 0
    rom.OE.value = 1
    rom.Address.value = 1
    circuit.run(ms=1)
    assert rom.DataOut.value == "X"
    _clock(circuit, rom)
    assert rom.DataOut.value == 0x3C


def test_rom_needs_file():
    """A ROM can't be made without a file"""
    with pytest.raises(ComponentException, match="needs a file"):
        ROM(Circuit(), "")


def test_memory_save_load(tmp_path):
    """The settings and the file are saved, the file relative to the circuit file"""
    (tmp_path / "data").mkdir()
    data = tmp_path / "data" / "rom.hex"
    data.write_text("11 22\n")
    circuit = Circuit(name="memories")
    ROM(circuit, data, address_width=4, data_width=12, mode="sync")
    RAM(circuit, mode="async", output_enable=True)
    circuit.to_json_file(tmp_path / "memories.json")
    settings = {c.name: c.settings for c in circuit.to_dataclass(str(tmp_path)).components}
    assert settings["ROM"]["path"] == "data/rom.hex"
    assert "path" not in settings["RAM"]

    loaded = Circuit()
    loaded.from_json_file(tmp_path / "memories.json")
    loaded.init()
    rom = loaded.get_component("ROM")
    ram = loaded.get_component("RAM")
    assert isinstance(rom, ROM)
    assert isinstance(ram, RAM)
    assert rom.settings_to_dict() == settings["ROM"]
    assert ram.settings_to_dict() == settings["RAM"]
    assert rom.read(1) == 0x22
    assert "OE" in _port_names(ram)


def test_memstdout(capsys):
    """Characters written to the address are printed, a newline prints the line"""
    circuit = Circuit()
    stdout = MemStdOut(circuit, address=0x8000)
    circuit.init()
    stdout.clk.value = 0
    stdout.Address.value = 0x8000
    stdout.WE.value = 1
    for char in b"Hi\n":
        stdout.DataIn.value = char
        _clock(circuit, stdout)
    assert capsys.readouterr().out.splitlines()[-1] == "StringOutput [line]: 'Hi'"


def test_memstdout_undefined_write_enable(capsys):
    """Nothing is printed when write enable is undefined"""
    circuit = Circuit()
    stdout = MemStdOut(circuit, address=0x8000)
    circuit.init()
    stdout.clk.value = 0
    stdout.Address.value = 0x8000
    stdout.DataIn.value = ord("A")
    _clock(circuit, stdout)
    assert capsys.readouterr().out == ""
