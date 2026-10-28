# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the list of recent circuit files"""

import os

import pytest

from digsim.app._recent_files import MAX_RECENT_FILES, with_recent, without_file


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


def test_with_recent():
    """The newest first, once, with absolute paths, and not more than the most"""
    paths = with_recent([], "a.circuit")
    assert paths == [os.path.abspath("a.circuit")]
    paths = with_recent(with_recent(paths, "b.circuit"), "a.circuit")
    assert paths == [os.path.abspath("a.circuit"), os.path.abspath("b.circuit")]
    for number in range(20):
        paths = with_recent(paths, f"{number}.circuit")
    assert len(paths) == MAX_RECENT_FILES
    assert paths[0] == os.path.abspath("19.circuit")


def test_without_file():
    assert without_file(["/a", "/b"], "/a") == ["/b"]
    assert without_file(["/a"], "/c") == ["/a"]
