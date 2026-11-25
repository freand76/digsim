# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
cocotb tests of verilog/cocotb_counter.sv, run with DigSim by test_cocotb.py (not by
pytest itself)
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge, Timer


async def reset(dut):
    """Reset the counter for a clock cycle"""
    dut.ena.value = 0
    dut.set.value = 0
    dut.din.value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst.value = 0


@cocotb.test
async def test_undefined_at_start(dut):
    """All the ports are undefined before anything drives them"""
    assert str(dut.clk.value) == "X"
    assert str(dut.count.value) == "XXXXXXXX"


@cocotb.test
async def test_load_and_count(dut):
    """The counter loads a value and counts from it"""
    Clock(dut.clk, 10, "ns").start()
    await reset(dut)
    dut.din.value = 10
    dut.set.value = 1
    await RisingEdge(dut.clk)
    dut.set.value = 0
    dut.ena.value = 1
    await Timer(1, "ns")
    assert dut.count.value == 10
    for expected in range(11, 21):
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        assert dut.count.value == expected


@cocotb.test
async def test_readonly_sees_the_old_value(dut):
    """In the time step of the edge, the flip-flops still have their old value"""
    Clock(dut.clk, 10, "ns", impl="gpi").start()
    await reset(dut)
    dut.ena.value = 1
    values = []
    for _ in range(4):
        await RisingEdge(dut.clk)
        await ReadOnly()
        values.append(int(dut.count.value))
    assert values == [0, 1, 2, 3]


@cocotb.test(expect_fail=True)
async def test_wrong_value_fails(dut):
    """A wrong expectation fails"""
    Clock(dut.clk, 10, "ns").start()
    await reset(dut)
    await Timer(1, "ns")
    assert dut.count.value == 1


@cocotb.test
async def test_plusarg(dut):
    """The plusargs of the command line reach the tests"""
    assert cocotb.plusargs["digsim_plusarg"] == "42"
