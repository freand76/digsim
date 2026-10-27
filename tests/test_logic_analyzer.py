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


def test_logic_analyzer_samples_before_a_change_at_the_same_time():
    """
    A clock edge at the time of a sample is sampled before the edge, also when the run
    is split in steps (like Step Clock), so a clock looks the same either way
    """
    from digsim.app._clock_step import step_clock
    from digsim.circuit.components import Clock

    def analyzer_run(stepped):
        circuit = Circuit()
        clock = Clock(circuit, frequency=5)
        analyzer = LogicAnalyzer(circuit, sample_rate=20)
        clock.O.wire = analyzer.A
        circuit.init()
        if stepped:
            for _ in range(6):
                step_clock(circuit)
        else:
            circuit.run_until(ns=1_199_999_999)
        return analyzer.signal_data()["A"][-20:]

    samples = analyzer_run(stepped=False)
    assert samples == analyzer_run(stepped=True)
    # The clock toggles every 100 ms, every second sample: two samples high, two low. The
    # last one is at 1150 ms, the clock is high from 1100 ms.
    assert samples[-8:] == [1, 0, 0, 1, 1, 0, 0, 1]


def test_logic_analyzer_cleared_by_init():
    """A new run from time 0 doesn't show the samples of the last one"""
    circuit = Circuit()
    analyzer = LogicAnalyzer(circuit, sample_rate=100)
    circuit.init()
    analyzer.A.value = 1
    circuit.run(ms=50)
    assert 1 in analyzer.signal_data()["A"]
    circuit.init()
    assert analyzer.signal_data()["A"] == [0] * 100
