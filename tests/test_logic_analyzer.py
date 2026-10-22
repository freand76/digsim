# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the logic analyzer component"""

from digsim.circuit import Circuit
from digsim.circuit.components import LogicAnalyzer


def test_logic_analyzer_samples():
    """The analyzer keeps the last 100 samples of each input"""
    circuit = Circuit()
    analyzer = LogicAnalyzer(circuit, sample_rate=100)
    circuit.init()
    analyzer.A.value = 1
    circuit.run(ms=50)
    data = analyzer.signal_data()
    assert len(data["A"]) == 100
    assert data["A"][-5:] == [1] * 5
    assert data["B"] == [0] * 100


def test_logic_analyzer_data_not_changed_in_place():
    """Data handed out to the GUI is not changed by later samples"""
    circuit = Circuit()
    analyzer = LogicAnalyzer(circuit, sample_rate=100)
    circuit.init()
    samples = analyzer.signal_data()["A"]
    analyzer.A.value = 1
    circuit.run(ms=50)
    assert samples == [0] * 100


def test_logic_analyzer_gui_default():
    """A logic analyzer added in the GUI samples at the rate of one made in Python"""
    default = LogicAnalyzer.get_parameters()["sample_rate"]["default"]
    assert default == LogicAnalyzer(Circuit()).parameter_get("sample_rate")
