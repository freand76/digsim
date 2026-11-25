# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
cocotb's pytest plugin with DigSim: test_cocotb.py runs this file with
pytest -p cocotb_tools._pytest.plugin --cocotb-simulator=digsim. test_counter() runs the
simulation, the async tests run in it.
"""

from pathlib import Path

import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools._pytest.hdl import HDL


COUNTER = Path(__file__).parent.parent / "verilog" / "cocotb_counter.sv"


@pytest.fixture(name="counter")
def counter_fixture(hdl: HDL) -> HDL:
    """The counter, synthesized"""
    hdl.toplevel = "counter"
    hdl.sources = (COUNTER,)
    hdl.build()
    return hdl


@pytest.mark.cocotb_runner
def test_counter(counter: HDL) -> None:
    """Run the async tests of this file on DigSim"""
    counter.test()


async def test_load_and_count(dut) -> None:
    """The counter loads a value and counts from it"""
    # Low at first: the first rising edge is after the inputs are set
    Clock(dut.clk, 10, "ns", start_high=False).start()
    dut.rst.value = 0
    dut.ena.value = 0
    dut.din.value = 7
    dut.set.value = 1
    await RisingEdge(dut.clk)
    dut.set.value = 0
    dut.ena.value = 1
    await Timer(1, "ns")
    assert dut.count.value == 7
    await RisingEdge(dut.clk)
    await Timer(1, "ns")
    assert dut.count.value == 8
    assert dut.value.value == 8


async def test_internal_signal(dut) -> None:
    """A signal inside a submodule"""
    assert str(dut.u_parity.odd_reg.value) in ("0", "1", "X")
