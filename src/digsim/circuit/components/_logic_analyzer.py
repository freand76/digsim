# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with Logic Analyzer component"""

from .atoms import CallbackComponent, PortOutDelta, PortWire


class LogicAnalyzer(CallbackComponent):
    """Logic Analyzer component class"""

    PORTLIST = ["A", "B", "C", "D", "E", "F", "G", "H"]

    def __init__(self, circuit, name=None, sample_rate=100):
        super().__init__(circuit, name)
        self.data_dict = {}
        for portname in self.PORTLIST:
            self.add_port(PortWire(self, portname))
            self.data_dict[portname] = [0] * 100
        self._feedback = PortOutDelta(self, "feedback")
        self._feedback.update_parent(True)
        self.parameter_set("sample_rate", sample_rate)
        self.reconfigure()

    def default_state(self):
        self._feedback.value = 1

    def update(self):
        if self._feedback.value == 1:
            self._feedback.value = 0
        else:
            self._feedback.value = 1

        for portname in self.PORTLIST:
            self.data_dict[portname].pop(0)
            value = 1 if self.port(portname).value == 1 else 0
            self.data_dict[portname].append(value)
        super().update()

    def reconfigure(self):
        sample_rate = self.parameter_get("sample_rate")
        period_ns = int(1000000000 / sample_rate)
        self._feedback.set_delay_ns(period_ns)

    def signal_data(self):
        """Get the logic analyzer signal data"""
        return self.data_dict

    @classmethod
    def get_parameters(cls):
        return {
            "sample_rate": {
                "type": "int",
                "min": 10,
                "max": 100,
                "default": 20,
                "description": "Sample rate in Hz",
                "reconfigurable": True,
            },
        }
