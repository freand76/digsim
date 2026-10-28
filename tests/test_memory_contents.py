# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the contents of a memory in the hex editor, and their files"""

import pytest

from digsim.app._memory_contents import (
    ascii_text,
    parse_word,
    read_contents,
    word_text,
    write_contents,
)


@pytest.mark.parametrize("name", ["data.hex", "data.bin"])
@pytest.mark.parametrize("data_width", [8, 12, 32])
@pytest.mark.parametrize("load_address", [0, 0x20])
def test_saved_contents_read_back(tmp_path, name, data_width, load_address):
    """What is saved is read again, in text and in binary"""
    words = [0] * 256
    words[load_address] = 1
    words[load_address + 5] = (1 << data_width) - 1
    # A gap of zeros, more than a row
    words[0xC3] = 0x42
    path = tmp_path / name
    write_contents(path, words, data_width, load_address)
    assert read_contents(path, 8, data_width, load_address) == words


def test_text_file(tmp_path):
    words = [0] * 64
    words[0:3] = [0xA, 0xB, 0xC]
    words[0x30] = 0xFF
    path = tmp_path / "data.mem"
    write_contents(path, words, 8, 0)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "0A 0B 0C" + " 00" * 13
    # Rows of zeros are skipped with an address
    assert lines[1] == "@30"
    assert lines[2].startswith("FF 00")


def test_binary_file_to_the_last_word(tmp_path):
    words = [0] * 16
    words[1] = 0x1234
    path = tmp_path / "data.bin"
    write_contents(path, words, 16, 0)
    assert path.read_bytes() == b"\x00\x00\x34\x12"


def test_empty_memory(tmp_path):
    path = tmp_path / "data.bin"
    write_contents(path, [0] * 16, 8, 0)
    assert path.read_bytes() == b""
    assert read_contents(None, 4, 8, 0) == [0] * 16


def test_words_before_the_load_address(tmp_path):
    words = [0] * 16
    words[1] = 7
    with pytest.raises(ValueError, match="before the load address"):
        write_contents(tmp_path / "data.bin", words, 8, 4)


@pytest.mark.parametrize(
    ("text", "value"), [("ff", 0xFF), ("0x1F", 0x1F), (" 7 ", 7), ("1_0", 0x10)]
)
def test_parse_word(text, value):
    assert parse_word(text, 8) == value


@pytest.mark.parametrize("text", ["100", "g", "", "-1"])
def test_parse_bad_word(text):
    with pytest.raises(ValueError):
        parse_word(text, 8)


def test_word_text_and_ascii():
    assert word_text(0xA, 12) == "00A"
    assert ascii_text([0x41, 0x00, 0x7A, 0x7F]) == "A.z."
