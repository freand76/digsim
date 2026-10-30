# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The contents of a RAM or ROM in the hex editor, and the file they are saved in (kept free
from Qt imports so that it can be tested without a display)
"""

from __future__ import annotations

from pathlib import Path

from digsim.circuit.components._memory import TEXT_FILE_TYPES, read_memory_file


# Words on a line of a text file, and in a row of the editor
WORDS_PER_ROW = 16


def word_digits(data_width: int) -> int:
    """The hexadecimal digits of a word"""
    return (data_width + 3) // 4


def word_text(value: int | str, data_width: int) -> str:
    """A word in hexadecimal, with all its digits, or "X" ("Z") in each digit"""
    if isinstance(value, str):
        return value * word_digits(data_width)
    return f"{value:0{word_digits(data_width)}X}"


def parse_word(text: str, data_width: int) -> int:
    """
    A word typed in hexadecimal, with or without 0x. Raises ValueError if it isn't one,
    or it doesn't fit in a word.
    """
    text = text.strip().replace("_", "")
    if text.lower().startswith("0x"):
        text = text[2:]
    value = int(text, 16)
    if not 0 <= value < 1 << data_width:
        raise ValueError(f"{text} does not fit in a word of {data_width} bits")
    return value


def has_ascii(data_width: int) -> bool:
    """Is a word whole bytes, that the editor shows as text too"""
    return data_width % 8 == 0


def ascii_text(values: list[int | str], data_width: int = 8) -> str:
    """
    Words as the characters of their bytes, the lowest byte first (like in a binary file),
    a dot for a byte that isn't printable or a word that is undefined
    """
    text = []
    for value in values:
        for byte in range(data_width // 8):
            code = value >> (8 * byte) & 0xFF if isinstance(value, int) else 0
            text.append(chr(code) if 0x20 <= code < 0x7F else ".")
    return "".join(text)


def defined_words(words: list[int | str]) -> tuple[list[int], int]:
    """The words with 0 for an undefined one ("X"), and how many were undefined"""
    undefined = sum(1 for value in words if isinstance(value, str))
    return [value if isinstance(value, int) else 0 for value in words], undefined


def read_contents(
    path: str | Path | None, address_width: int, data_width: int, load_address: int
) -> list[int]:
    """All the words of a memory, as its file fills it (zeros without a file)"""
    words = [0] * (1 << address_width)
    if path:
        for address, value in read_memory_file(
            path, address_width, data_width, load_address
        ).items():
            words[address] = value
    return words


def _text(words: list[int], data_width: int, load_address: int) -> str:
    """
    The words from the load address as text, like $readmemh reads: a line per row of
    words, and @ and the address (from the load address) after rows of zeros
    """
    lines: list[str] = []
    skipped = False
    for start in range(load_address, len(words), WORDS_PER_ROW):
        row = words[start : start + WORDS_PER_ROW]
        if not any(row):
            skipped = True
            continue
        if skipped:
            lines.append(f"@{start - load_address:X}")
        skipped = False
        lines.append(" ".join(word_text(value, data_width) for value in row))
    return "\n".join(lines) + "\n" if lines else ""


def _binary(words: list[int], data_width: int, load_address: int) -> bytes:
    """The words from the load address to the last one that isn't zero, little-endian"""
    used = [address for address in range(load_address, len(words)) if words[address]]
    if not used:
        return b""
    word_bytes = (data_width + 7) // 8
    return b"".join(
        value.to_bytes(word_bytes, "little") for value in words[load_address : used[-1] + 1]
    )


def write_contents(path: str | Path, words: list[int], data_width: int, load_address: int) -> None:
    """
    Save the words of a memory in a file that it is loaded from at the load address: text
    for .hex, .mem and .txt files, binary for others (see read_memory_file). The words
    before the load address can't be in the file, they must be zero.
    """
    if any(words[:load_address]):
        raise ValueError(f"The words before the load address {load_address:#x} must be 0")
    file_path = Path(path)
    if file_path.suffix.lower() in TEXT_FILE_TYPES:
        file_path.write_text(_text(words, data_width, load_address), encoding="utf-8")
    else:
        file_path.write_bytes(_binary(words, data_width, load_address))
