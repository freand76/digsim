# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import CallbackComponent, PortIn


class HexDigit(CallbackComponent):

    VAL_TO_SEGMENTS = {
        0: "ABCDEF",
        1: "BC",
        2: "ABDEG",
        3: "ABCDG",
        4: "BCFG",
        5: "ACDFG",
        6: "ACDEFG",
        7: "ABC",
        8: "ABCDEFG",
        9: "ABCDFG",
        10: "ABCEFG",
        11: "CDEFG",
        12: "ADEF",
        13: "BCDEG",
        14: "ADEFG",
        15: "AEFG",
        -1: "",
    }

    def __init__(self, circuit, name="HexDigit", callback=None, dot=False):
        super().__init__(circuit, name, callback)
        self.add_port(PortIn(self, "val", width=4))
        self._dot = dot
        if self._dot:
            self.add_port(PortIn(self, "dot"))

    def value(self):
        return self.val.value

    def dot_active(self):
        if self._dot:
            return self.dot.has_driver() and self.dot.value == 1
        return False

    def segments(self):
        segments = self.VAL_TO_SEGMENTS.get(self.value(), "")
        if self.dot_active():
            segments += "."
        return segments
