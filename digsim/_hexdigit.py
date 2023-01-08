# pylint: disable=no-member

from ._component import CallbackComponent
from ._port import ComponentPort, PortDirection, SignalLevel


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

    def __init__(self, circuit, name="LED", callback=None, dot=False):
        super().__init__(circuit, name, callback)
        self._dot = dot
        self.add_port(ComponentPort(self, "I0", PortDirection.IN))
        self.add_port(ComponentPort(self, "I1", PortDirection.IN))
        self.add_port(ComponentPort(self, "I2", PortDirection.IN))
        self.add_port(ComponentPort(self, "I3", PortDirection.IN))
        if self._dot:
            self.add_port(ComponentPort(self, "dot", PortDirection.IN))

    def value(self):
        if SignalLevel.UNKNOWN in [
            self.I0.level,
            self.I1.level,
            self.I2.level,
            self.I3.level,
        ]:
            return -1

        return self.I3.intval << 3 | self.I2.intval << 2 | self.I1.intval << 1 | self.I0.intval

    def dot_active(self):
        if self._dot:
            return self.dot.level == SignalLevel.HIGH
        return False

    def segments(self):
        segments = self.VAL_TO_SEGMENTS[self.value()]
        if self.dot_active():
            segments += "."
        return segments
