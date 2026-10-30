# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the HD44780 LCD component"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import HD44780, CircuitInOut, CircuitInput


BLANK = " " * 16


def lcd_circuit():
    """An LCD, after the circuit is initialized"""
    circuit = Circuit()
    lcd = HD44780(circuit)
    circuit.init()
    return circuit, lcd


def pulse(lcd, rs, rw):
    """An E pulse, with RS and RW"""
    lcd.RS.value = rs
    lcd.RW.value = rw
    lcd.E.value = 1
    lcd.E.value = 0


def write(lcd, rs, byte, bits=range(8)):
    """Write a byte, or a nibble on D4 to D7 (bits=range(4, 8))"""
    for index, bit in enumerate(bits):
        lcd.port(f"D{bit}").value = (byte >> index) & 1
    pulse(lcd, rs, 0)


def write4(lcd, rs, byte):
    """Write a byte in 4-bit mode, the high nibble first"""
    write(lcd, rs, byte >> 4, range(4, 8))
    write(lcd, rs, byte & 0xF, range(4, 8))


def text(lcd, string):
    for char in string:
        write(lcd, 1, ord(char))


def setup_8bit(lcd, display=0x0C):
    """8-bit mode, two lines, the display on, increment"""
    write(lcd, 0, 0x38)
    write(lcd, 0, display)
    write(lcd, 0, 0x06)
    write(lcd, 0, 0x01)


def test_ports():
    """RS, RW, E and the data pins"""
    lcd = HD44780(Circuit())
    assert [port.name() for port in lcd.ports] == ["RS", "RW", "E"] + [
        f"D{bit}" for bit in range(8)
    ]
    assert all(lcd.port(f"D{bit}").is_inout() for bit in range(8))


def test_power_on():
    """Spaces and the display off, in one-line mode"""
    _, lcd = lcd_circuit()
    assert lcd.lines() == [BLANK, BLANK]
    assert lcd.pixels()[0][0] == (0,) * 8
    assert lcd.address == 0


def test_write_text():
    """Text on both lines, with Set DDRAM address"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    text(lcd, "Hello, World!")
    write(lcd, 0, 0x80 | 0x40)
    text(lcd, "DigSim")
    assert lcd.lines() == ["Hello, World!   ", "DigSim          "]
    assert lcd.read_ddram(0x40) == ord("D")
    assert lcd.pixels()[0][0] == lcd.glyph(ord("H"))


def test_one_line_mode():
    """Without N, only the first line is shown, and the DDRAM is one line of 80"""
    _, lcd = lcd_circuit()
    write(lcd, 0, 0x30)
    write(lcd, 0, 0x0C)
    write(lcd, 0, 0x80 | 40)
    text(lcd, "x")
    assert lcd.lines() == [BLANK, BLANK]
    write(lcd, 0, 0x80)
    text(lcd, "ab")
    assert lcd.lines() == ["ab" + " " * 14, BLANK]


def test_address_wraps_to_next_line():
    """In two-line mode the address goes from the end of a line to the next"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    write(lcd, 0, 0x80 | 0x27)
    text(lcd, "ab")
    assert lcd.address == 0x41
    assert lcd.read_ddram(0x27) == ord("a")
    assert lcd.read_ddram(0x40) == ord("b")
    write(lcd, 0, 0x80 | 0x67)
    text(lcd, "c")
    assert lcd.address == 0x00


def test_four_bit_mode():
    """The usual initialization of 4-bit mode, on D4 to D7 only"""
    _, lcd = lcd_circuit()
    for nibble in (0x3, 0x3, 0x3, 0x2):
        write(lcd, 0, nibble, range(4, 8))
    write4(lcd, 0, 0x28)
    write4(lcd, 0, 0x0C)
    write4(lcd, 0, 0x01)
    write4(lcd, 0, 0x06)
    for char in "4-bit":
        write4(lcd, 1, ord(char))
    assert lcd.lines() == ["4-bit" + " " * 11, BLANK]


def test_clear_and_home():
    """Clear fills the DDRAM with spaces, home moves back the address and the shift"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    text(lcd, "abc")
    write(lcd, 0, 0x18)
    assert lcd.lines()[0] == "bc" + " " * 14
    write(lcd, 0, 0x02)
    assert lcd.address == 0
    assert lcd.lines()[0] == "abc" + " " * 13
    write(lcd, 0, 0x01)
    assert lcd.lines() == [BLANK, BLANK]


def test_entry_mode_decrement_and_shift():
    """With I/D 0 the address counts down, with S the display shifts on each write"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    write(lcd, 0, 0x80 | 5)
    write(lcd, 0, 0x04)
    text(lcd, "ab")
    assert lcd.address == 3
    assert lcd.lines()[0] == "    ba" + " " * 10
    write(lcd, 0, 0x01)
    write(lcd, 0, 0x80 | 16)
    write(lcd, 0, 0x07)
    text(lcd, "xy")
    assert lcd.lines()[0] == " " * 14 + "xy"


def test_cursor_shift():
    """Cursor shift moves the address counter"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    write(lcd, 0, 0x14)
    write(lcd, 0, 0x14)
    write(lcd, 0, 0x10)
    assert lcd.address == 1


def test_custom_character():
    """A character of the CGRAM is shown for codes 0 to 7, and 8 to 15"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    heart = [0x00, 0x0A, 0x1F, 0x1F, 0x0E, 0x04, 0x00, 0x00]
    write(lcd, 0, 0x40 | 8)
    for row in heart:
        write(lcd, 1, row)
    write(lcd, 0, 0x80)
    write(lcd, 1, 1)
    write(lcd, 1, 9)
    assert lcd.pixels()[0][0] == tuple(heart)
    assert lcd.pixels()[0][1] == tuple(heart)
    assert lcd.lines()[0][:2] == "\x01\x09"


def test_cursor_and_blink():
    """The cursor is the bottom row, a blinking cursor is a block every other 409.6 ms"""
    circuit, lcd = lcd_circuit()
    setup_8bit(lcd, display=0x0E)
    text(lcd, "A")
    assert lcd.pixels()[0][1] == (0,) * 7 + (0x1F,)
    write(lcd, 0, 0x0D)
    assert lcd.pixels()[0][1] == (0,) * 8
    circuit.run(ms=410)
    assert lcd.pixels()[0][1] == (0x1F,) * 8
    circuit.run(ms=410)
    assert lcd.pixels()[0][1] == (0,) * 8
    write(lcd, 0, 0x0C)
    circuit.run(ms=1000)
    assert lcd.pixels()[0][1] == (0,) * 8


def test_character_rom():
    """The A00 ROM: the yen sign and the arrows instead of backslash and tilde"""
    lcd = HD44780(Circuit())
    assert lcd.glyph(ord("A")) == (0x0E, 0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x00)
    assert lcd.glyph(0xFF) == (0x1F,) * 8
    assert lcd.glyph(0x20) == (0,) * 8
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    for code in (0x5C, 0x7E, 0x7F, 0xDF, 0xB1, 0xF4):
        write(lcd, 1, code)
    assert lcd.lines()[0][:6] == "¥→←ﾟｱΩ"


def test_undefined_data_is_ignored():
    """A write with an "X" on a data pin is not done"""
    _, lcd = lcd_circuit()
    setup_8bit(lcd)
    lcd.D3.value = "X"
    pulse(lcd, 1, 0)
    assert lcd.address == 0


@pytest.mark.parametrize("four_bit", [False, True])
def test_read_in_a_circuit(four_bit):
    """The busy flag and address, and data, are read through wires while E is 1"""
    circuit = Circuit()
    lcd = HD44780(circuit)
    rs = CircuitInput(circuit, label="rs")
    rw = CircuitInput(circuit, label="rw")
    enable = CircuitInput(circuit, label="e")
    rs.port("rs").wire = lcd.RS
    rw.port("rw").wire = lcd.RW
    enable.port("e").wire = lcd.E
    pins = []
    for bit in range(8):
        pin = CircuitInOut(circuit, label=f"d{bit}")
        pin.port(f"d{bit}").wire = lcd.port(f"D{bit}")
        lcd.port(f"D{bit}").wire = pin.port(f"d{bit}")
        pins.append(pin)
    circuit.init()

    def cycle(rs_value, rw_value, byte=None, bits=range(8)):
        rs.set_value(rs_value)
        rw.set_value(rw_value)
        for index, bit in enumerate(bits):
            pins[bit].set_value("Z" if byte is None else (byte >> index) & 1)
        circuit.run(ns=100)
        enable.set_value(1)
        circuit.run(ns=100)
        read = sum(
            (pins[bit].value << index) for index, bit in enumerate(bits)
        )  # The wire while E is 1
        enable.set_value(0)
        circuit.run(ns=100)
        return read

    if four_bit:
        cycle(0, 0, 0x2, range(4, 8))
        bits = range(4, 8)

        def transfer(rs_value, rw_value, byte=None):
            high = cycle(rs_value, rw_value, None if byte is None else byte >> 4, bits)
            low = cycle(rs_value, rw_value, None if byte is None else byte & 0xF, bits)
            return high << 4 | low

    else:

        def transfer(rs_value, rw_value, byte=None):
            return cycle(rs_value, rw_value, byte)

    transfer(0, 0, 0x28 if four_bit else 0x38)
    transfer(0, 0, 0x0C)
    transfer(0, 0, 0x01)
    transfer(0, 0, 0x06)
    for char in "Hi":
        transfer(1, 0, ord(char))
    assert lcd.lines()[0] == "Hi" + " " * 14
    # Not busy, at address 2
    assert transfer(0, 1) == 0x02
    transfer(0, 0, 0x80)
    assert transfer(1, 1) == ord("H")
    assert transfer(1, 1) == ord("i")
    assert lcd.address == 2
    # The data pins are released after a read
    assert all(lcd.port(f"D{bit}").value == "Z" for bit in range(8))


def test_backlight_saved_and_loaded(tmp_path):
    """The backlight color is saved, green if not given"""
    circuit = Circuit(name="lcd")
    assert HD44780(circuit, "green").backlight == "green"
    HD44780(circuit, "blue", backlight="blue")
    circuit.to_json_file(tmp_path / "lcd.json")
    loaded = Circuit()
    loaded.from_json_file(tmp_path / "lcd.json")
    assert loaded.get_component("blue").backlight == "blue"
    backlight = HD44780.get_parameters()["backlight"]
    assert backlight["default"] == "green"
    assert backlight["reconfigurable"]
