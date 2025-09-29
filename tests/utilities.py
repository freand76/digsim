# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Utility module for tests"""

_L = 0
_H = 1
_X = "X"


def inv(val):
    """Invert logic level 0 => 1 and 1 => 0"""
    return _L if val == _H else _H
