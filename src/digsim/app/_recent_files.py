# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The circuit files opened or saved last, for File > Open Recent (kept free from Qt imports
so that it can be tested without a display)
"""

from __future__ import annotations

import os


# The most files in the list
MAX_RECENT_FILES = 8


def with_recent(paths: list[str], path: str) -> list[str]:
    """The list with a file opened or saved now first, once, and the oldest ones dropped"""
    path = os.path.abspath(path)
    return [path, *(other for other in paths if other != path)][:MAX_RECENT_FILES]


def without_file(paths: list[str], path: str) -> list[str]:
    """The list without a file, like one that is gone"""
    return [other for other in paths if other != path]
