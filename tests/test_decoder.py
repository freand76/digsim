# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test the decoder, the demultiplexer and the MUX with 16 inputs"""

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import MUX, Decoder, Demultiplexer, StaticValue


@pytest.mark.parametrize(("select", "high"), [(0, "Y0"), (2, "Y2"), (3, "Y3")])
def test_decoder(select, high):
    circuit = Circuit()
    decoder = Decoder(circuit, select=2, enable=True)
    StaticValue(circuit, width=2, value=select).O.wire = decoder.S
    StaticValue(circuit, value=1).O.wire = decoder.EN
    circuit.init()
    circuit.run(ns=10)
    assert {port.name(): port.value for port in decoder.outports()} == {
        f"Y{index}": int(f"Y{index}" == high) for index in range(4)
    }


def test_decoder_disabled_and_undefined():
    """All outputs are 0 while it isn't enabled, X with an undefined select"""
    circuit = Circuit()
    decoder = Decoder(circuit, select=1, enable=True)
    enable = StaticValue(circuit, value=0)
    enable.O.wire = decoder.EN
    circuit.init()
    circuit.run(ns=10)
    assert [port.value for port in decoder.outports()] == [0, 0]
    assert len(Decoder(Circuit(), select=4).outports()) == 16


def test_demultiplexer():
    """The selected output is the input, the others are 0"""
    circuit = Circuit()
    demux = Demultiplexer(circuit, select=2, width=8)
    StaticValue(circuit, width=8, value=0xA5).O.wire = demux.I
    StaticValue(circuit, width=2, value=1).O.wire = demux.S
    circuit.init()
    circuit.run(ns=10)
    assert [port.value for port in demux.outports()] == [0, 0xA5, 0, 0]


def test_mux_with_16_inputs():
    circuit = Circuit()
    mux = MUX(circuit, ports=16, width=4)
    for index, port in enumerate(mux.inports()[:16]):
        StaticValue(circuit, width=4, value=index).O.wire = port
    StaticValue(circuit, width=4, value=13).O.wire = mux.S
    circuit.init()
    circuit.run(ns=10)
    assert mux.Y.value == 13
