# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Module with the HD44780 character LCD component, a 16x2 LCD module with a backlight"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._hd44780_rom import CHARACTER_ROM, TEXT
from .atoms import VALUE_TYPE, CallbackComponent, Parameter, PortIn, PortInOut, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit

COLUMNS = 16
ROWS = 2
# The DDRAM has 80 characters, a line of 40 in two-line mode
DDRAM_SIZE = 80
LINE_LENGTH = 40
# The address of the second line in two-line mode
LINE2_ADDRESS = 0x40
CGRAM_SIZE = 64
# The cursor blinks at 1.6 Hz (with a 250 kHz oscillator), this is half the period
BLINK_NS = 409_600_000

BACKLIGHTS = ["green", "blue", "amber", "white", "red"]


class HD44780(CallbackComponent):
    """
    A 16x2 character LCD module with an HD44780 controller and a backlight, programmed
    like the real one, with the A00 (English and Japanese) character ROM.

    The controller reads RS and RW, and the data on D0 to D7, on the falling edge of E. A
    write with RS 0 is an instruction and with RS 1 data for the DDRAM or the CGRAM.
    While E is 1 with RW 1 it drives the data pins: with RS 0 the busy flag (bit 7) and
    the address counter, with RS 1 the data at the address. An instruction is done at
    once, so the busy flag is always 0.

    After a 4-bit Function Set (DL 0) the data is on D4 to D7, the high nibble first, and
    D0 to D3 are not used. The data pins that nothing drives are 1, the controller has
    pull-ups on them.

    It starts like after power on: in 8-bit mode with one line (only the first line of
    the display is shown), the display off and the DDRAM filled with spaces. Function Set
    with N 1 selects two lines.

    Ports:
        RS: Register select input, 0 for an instruction and 1 for data.
        RW: Read/write input, 0 to write and 1 to read.
        E: Enable input, a write is done on its falling edge.
        D0, D1, ..., D7: Data inout ports.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        backlight: The color of the backlight in the GUI: "green" (yellow-green with dark
            characters), "blue" (white characters), "amber", "white" or "red".
    """

    def __init__(
        self, circuit: Circuit, name: str | None = None, backlight: str = "green"
    ) -> None:
        super().__init__(circuit, name)
        # Before the ports, wiring them updates the component
        self._blink_level = 0
        self._reset_state()
        self.add_port(PortIn(self, "RS"))
        self.add_port(PortIn(self, "RW"))
        self.add_port(PortIn(self, "E"))
        # A driver for each data pin, and an input for each pin it reads, like CircuitInOut
        self._drivers: list[PortOutDelta] = []
        self._readers: list[PortIn] = []
        for bit in range(8):
            pin = PortInOut(self, f"D{bit}")
            pin.set_tristate()
            self.add_port(pin)
            driver = PortOutDelta(self, f"D{bit}_driver", delay_ns=0)
            driver.set_tristate()
            driver.wire = pin.get_drive_bit(0)
            self._drivers.append(driver)
            reader = PortIn(self, f"D{bit}_reader")
            pin.get_bit(0).wire = reader
            self._readers.append(reader)
        # Toggles the blink of the cursor
        self._blink_timer = PortOutDelta(self, "blink_timer", delay_ns=BLINK_NS)
        self._blink_timer.update_parent(True)
        self.parameter_set("backlight", backlight)

    def _reset_state(self) -> None:
        """The state after power on"""
        self._ddram = [0x20] * DDRAM_SIZE
        self._cgram = [0] * CGRAM_SIZE
        # The address counter, and if it addresses the CGRAM
        self._address = 0
        self._cgram_selected = False
        self._increment = True
        self._shift_on_write = False
        self._display_on = False
        self._cursor_on = False
        self._blink_on = False
        self._eight_bit = True
        self._two_lines = False
        self._large_font = False
        # How far the display is shifted left
        self._shift = 0
        # In 4-bit mode: the high nibble of a transfer, None until it is done
        self._high_nibble: int | None = None
        # The blink phase where the character is replaced by a block, and its next toggle
        self._blink_dark = False
        self._blink_at_ns: int | None = None
        self._driven: VALUE_TYPE = "Z"

    def init(self) -> None:
        super().init()
        for port in [*self._drivers, *self._readers, self._blink_timer]:
            port.init()

    def default_state(self) -> None:
        self._reset_state()
        for driver in self._drivers:
            driver.value = "Z"
        self._changed()

    @property
    def backlight(self) -> str:
        """The color of the backlight in the GUI"""
        return self.parameter_get("backlight")

    def _changed(self) -> None:
        """The display may have changed, the GUI repaints it"""
        super().update()

    def _bus(self) -> int | None:
        """The byte on the data pins, the nibble on D4 to D7 in 4-bit mode, None with an "X" """
        value = 0
        pins = self._readers[4:] if not self._eight_bit else self._readers
        for bit, reader in enumerate(pins):
            level = reader.value
            if level == "Z":
                # The pull-ups
                level = 1
            if not isinstance(level, int):
                return None
            value |= level << bit
        return value

    def _drive(self, value: VALUE_TYPE) -> None:
        """Drive the data pins with a byte (a nibble on D4 to D7 in 4-bit mode), or "Z" """
        if value == self._driven:
            return
        self._driven = value
        for bit, driver in enumerate(self._drivers):
            if not isinstance(value, int) or (not self._eight_bit and bit < 4):
                driver.value = "Z"
            else:
                shift = bit if self._eight_bit else bit - 4
                driver.value = (value >> shift) & 1

    def _read_byte(self, rs: int) -> int:
        """The byte that a read returns"""
        if rs == 0:
            # The busy flag is 0
            return self._address
        if self._cgram_selected:
            return self._cgram[self._address]
        return self._ddram[self._ddram_index(self._address)]

    def _read_output(self, rs: int) -> int:
        """What the data pins show during a read, a nibble of the byte in 4-bit mode"""
        byte = self._read_byte(rs)
        if self._eight_bit:
            return byte
        return byte >> 4 if self._high_nibble is None else byte & 0xF

    def update(self) -> None:
        falling_edge = self.E.is_falling_edge()
        now = self.circuit.time_ns
        if self._blink_at_ns is not None and now >= self._blink_at_ns:
            self._blink_dark = not self._blink_dark
            self._blink_at_ns = None
            self._update_blink()
            self._changed()
        rs, rw = self.RS.value, self.RW.value
        if falling_edge and isinstance(rs, int) and isinstance(rw, int):
            if rw == 0:
                self._write(rs)
            else:
                self._read_done(rs)
        # While E is 1 with RW 1, the controller drives the data pins
        if self.E.value == 1 and rw == 1 and isinstance(rs, int):
            self._drive(self._read_output(rs))
        else:
            self._drive("Z")

    def _transfer(self) -> int | None:
        """The byte of a write, None while half of it is transferred in 4-bit mode"""
        bus = self._bus()
        if bus is None:
            self._high_nibble = None
            return None
        if self._eight_bit:
            return bus
        if self._high_nibble is None:
            self._high_nibble = bus
            return None
        byte = self._high_nibble << 4 | bus
        self._high_nibble = None
        return byte

    def _write(self, rs: int) -> None:
        byte = self._transfer()
        if byte is None:
            return
        if rs == 0:
            self._instruction(byte)
        else:
            self._write_data(byte)
        self._update_blink()
        self._changed()

    def _read_done(self, rs: int) -> None:
        """The end of a read: after a data read the address counter moves"""
        if not self._eight_bit:
            if self._high_nibble is None:
                # A placeholder, the next nibble is the low one
                self._high_nibble = 0
                return
            self._high_nibble = None
        if rs == 1:
            self._move_address(self._increment)
            self._update_blink()
            self._changed()

    def _instruction(self, byte: int) -> None:
        if byte & 0x80:
            # Set DDRAM address
            self._address = self._valid_ddram_address(byte & 0x7F)
            self._cgram_selected = False
        elif byte & 0x40:
            # Set CGRAM address
            self._address = byte & 0x3F
            self._cgram_selected = True
        elif byte & 0x20:
            # Function set
            self._eight_bit = bool(byte & 0x10)
            self._two_lines = bool(byte & 0x08)
            self._large_font = bool(byte & 0x04)
            self._address = self._valid_ddram_address(self._address)
        elif byte & 0x10:
            # Cursor or display shift, right or left
            right = bool(byte & 0x04)
            if byte & 0x08:
                self._shift_display(not right)
            else:
                self._move_address(right)
        elif byte & 0x08:
            # Display on/off control
            self._display_on = bool(byte & 0x04)
            self._cursor_on = bool(byte & 0x02)
            self._blink_on = bool(byte & 0x01)
        elif byte & 0x04:
            # Entry mode set
            self._increment = bool(byte & 0x02)
            self._shift_on_write = bool(byte & 0x01)
        elif byte & 0x02:
            # Return home
            self._address = 0
            self._cgram_selected = False
            self._shift = 0
        elif byte & 0x01:
            # Clear display
            self._ddram = [0x20] * DDRAM_SIZE
            self._address = 0
            self._cgram_selected = False
            self._shift = 0
            self._increment = True

    def _write_data(self, byte: int) -> None:
        if self._cgram_selected:
            self._cgram[self._address] = byte
        else:
            self._ddram[self._ddram_index(self._address)] = byte
            if self._shift_on_write:
                self._shift_display(self._increment)
        self._move_address(self._increment)

    def _shift_display(self, left: bool) -> None:
        """Shift the display one character left or right"""
        length = LINE_LENGTH if self._two_lines else DDRAM_SIZE
        self._shift = (self._shift + (1 if left else -1)) % length

    def _valid_ddram_address(self, address: int) -> int:
        """A DDRAM address, the ones between the lines are not used"""
        if self._two_lines:
            if address >= LINE2_ADDRESS:
                return min(address, LINE2_ADDRESS + LINE_LENGTH - 1)
            return min(address, LINE_LENGTH - 1)
        return min(address, DDRAM_SIZE - 1)

    def _ddram_index(self, address: int) -> int:
        """The index in the DDRAM of an address"""
        if self._two_lines and address >= LINE2_ADDRESS:
            return LINE_LENGTH + address - LINE2_ADDRESS
        return address

    def _move_address(self, increment: bool) -> None:
        """Move the address counter one step, it wraps around"""
        step = 1 if increment else -1
        if self._cgram_selected:
            self._address = (self._address + step) % CGRAM_SIZE
            return
        index = (self._ddram_index(self._address) + step) % DDRAM_SIZE
        if self._two_lines and index >= LINE_LENGTH:
            self._address = LINE2_ADDRESS + index - LINE_LENGTH
        else:
            self._address = index

    def _cursor_cell(self) -> tuple[int, int] | None:
        """The (row, column) of the address counter on the display, None if not shown"""
        if self._cgram_selected:
            return None
        index = self._ddram_index(self._address)
        length = LINE_LENGTH if self._two_lines else DDRAM_SIZE
        row, position = divmod(index, length)
        if row >= ROWS:
            return None
        column = (position - self._shift) % length
        return (row, column) if column < COLUMNS else None

    def _update_blink(self) -> None:
        """Run the blink timer while the cursor blinks"""
        blinks = self._display_on and self._blink_on
        if not blinks:
            self._blink_dark = False
            self._blink_at_ns = None
            return
        if self._blink_at_ns is None:
            self._blink_at_ns = self.circuit.time_ns + BLINK_NS
            # A change, so that the timer is an event
            self._blink_level ^= 1
            self._blink_timer.value = self._blink_level

    def codes(self) -> list[list[int | None]]:
        """
        The character code shown in each place of the display, a list for each line. In
        one-line mode the second line is None.
        """
        length = LINE_LENGTH if self._two_lines else DDRAM_SIZE
        lines: list[list[int | None]] = []
        for row in range(ROWS):
            if row and not self._two_lines:
                lines.append([None] * COLUMNS)
                continue
            lines.append(
                [
                    self._ddram[row * length + (column + self._shift) % length]
                    for column in range(COLUMNS)
                ]
            )
        return lines

    def lines(self) -> list[str]:
        """
        The text of the two lines of the display, 16 characters each, also while the
        display is off. A character of the CGRAM (codes 0 to 15) is chr(code), and a code
        without a character is a space.
        """
        return [
            "".join(
                " " if code is None else chr(code) if code < 0x10 else TEXT.get(code, " ")
                for code in line
            )
            for line in self.codes()
        ]

    @staticmethod
    def rom_glyph(code: int) -> tuple[int, ...]:
        """
        The glyph of a code in the character ROM, see glyph(). Codes 0 to 15 are blank.

        Args:
            code: The character code, 0 to 255.
        """
        return CHARACTER_ROM[code]

    def glyph(self, code: int) -> tuple[int, ...]:
        """
        The 8 rows of 5 pixels of a character, the top row first, the left pixel in bit
        4. Codes 0 to 15 are the 8 characters of the CGRAM (twice).

        Args:
            code: The character code, 0 to 255.
        """
        if code < 0x10:
            start = (code & 0x07) * 8
            return tuple(row & 0x1F for row in self._cgram[start : start + 8])
        return CHARACTER_ROM[code]

    def pixels(self) -> list[list[tuple[int, ...]]]:
        """
        What the display shows: the rows of pixels of each character (see glyph()), a list
        for each line, with the cursor. Nothing is shown while the display is off.
        """
        blank = (0,) * 8
        cursor = self._cursor_cell()
        shown: list[list[tuple[int, ...]]] = []
        for row, line in enumerate(self.codes()):
            cells: list[tuple[int, ...]] = []
            for column, code in enumerate(line):
                if not self._display_on or code is None:
                    cells.append(blank)
                    continue
                glyph = self.glyph(code)
                if cursor == (row, column):
                    if self._blink_on and self._blink_dark:
                        glyph = (0x1F,) * 8
                    elif self._cursor_on:
                        glyph = (*glyph[:7], 0x1F)
                cells.append(glyph)
            shown.append(cells)
        return shown

    def read_ddram(self, address: int) -> int:
        """
        Return the character code at a DDRAM address.

        Args:
            address: The address, 0x00 to 0x27 and 0x40 to 0x67 in two-line mode, otherwise
                0x00 to 0x4F.
        """
        return self._ddram[self._ddram_index(address)]

    @property
    def address(self) -> int:
        """The address counter, in the DDRAM or the CGRAM"""
        return self._address

    @classmethod
    def get_parameters(cls) -> dict[str, Parameter]:
        return {
            "backlight": {
                "type": "list",
                "items": BACKLIGHTS,
                "default": "green",
                "description": "Backlight color",
                "reconfigurable": True,
            },
        }
