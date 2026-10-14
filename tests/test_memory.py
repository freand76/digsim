# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the memory components"""

from digsim.circuit import Circuit
from digsim.circuit.components import Mem64kByte, MemStdOut


def _clock(circuit, memory):
    memory.clk.value = 1
    circuit.run(ms=1)
    memory.clk.value = 0
    circuit.run(ms=1)


def test_mem64kbyte_write_read(tmp_path):
    """Written data is read back, and ROM data is loaded at its address"""
    rom = tmp_path / "rom.bin"
    rom.write_bytes(bytes([0x12, 0x34]))
    circuit = Circuit()
    memory = Mem64kByte(circuit, rom_filename=rom, rom_address=0x100)
    circuit.init()
    memory.clk.value = 0
    memory.WE.value = 0
    memory.Address.value = 0x101
    _clock(circuit, memory)
    assert memory.DataOut.value == 0x34
    memory.WE.value = 1
    memory.Address.value = 0x200
    memory.DataIn.value = 0xAB
    _clock(circuit, memory)
    memory.WE.value = 0
    _clock(circuit, memory)
    assert memory.DataOut.value == 0xAB


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
