# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from digsim.circuit import Circuit
from digsim.circuit.components import DFFE_PP0P
from digsim.circuit.components.atoms import SignalLevel


UNKNOWN = SignalLevel.UNKNOWN
HIGH = SignalLevel.HIGH
LOW = SignalLevel.LOW


def do_clock(circuit, signal):
    signal.level = HIGH
    circuit.run(ms=1)
    signal.level = LOW
    circuit.run(ms=1)


def test_dff():
    circuit = Circuit()
    _dut = DFFE_PP0P(circuit)

    _dut.E.level = LOW
    _dut.C.level = LOW
    _dut.R.level = LOW
    _dut.D.level = LOW
    assert _dut.Q.level == UNKNOWN
    circuit.run(ms=1)
    assert _dut.Q.level == UNKNOWN

    # No change for enable and data while no clock
    _dut.E.level = HIGH
    _dut.D.level = HIGH
    circuit.run(ms=1)
    assert _dut.Q.level == UNKNOWN

    # No change for enable and data while no clock
    _dut.E.level = LOW
    _dut.D.level = LOW
    circuit.run(ms=1)
    assert _dut.Q.level == UNKNOWN

    # Update when enable is high (D=0)
    _dut.E.level = HIGH
    do_clock(circuit, _dut.C)
    assert _dut.Q.level == LOW

    # No update when enable is low
    _dut.E.level = LOW
    _dut.D.level = HIGH
    do_clock(circuit, _dut.C)
    assert _dut.Q.level == LOW

    # Update when enable is high (D=1)
    _dut.E.level = HIGH
    do_clock(circuit, _dut.C)
    assert _dut.Q.level == HIGH

    # No change when enable is low
    _dut.E.level = LOW
    do_clock(circuit, _dut.C)
    assert _dut.Q.level == HIGH

    # Make sure cleared after reset
    _dut.R.level = HIGH
    circuit.run(ms=1)
    assert _dut.Q.level == LOW
