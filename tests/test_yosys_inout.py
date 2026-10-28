# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test inout ports (PortInOut) and the inout ports of Verilog designs"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import (
    Bus2Wires,
    DipSwitch,
    PortConnectionError,
    PortInOut,
    PushButton,
    StaticValue,
    TristateBuffer,
    YosysComponent,
    YosysComponentException,
)
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


VERILOG = Path(__file__).parent / "verilog" / "inout.v"
ROOT = Path(__file__).parents[1]
BUS_REGISTER = ROOT / "examples" / "yosys_inout" / "bus_register.v"
WALKIE_TALKIE = ROOT / "circuits" / "walkie_talkie" / "walkie_talkie.circuit"


def _netlist(top, functional=False):
    synthesis = Synthesis([str(VERILOG)], top, functional=functional)
    return YosysNetlist(**synthesis.synth_to_dict(silent=True))


def _design(circuit, top, functional=False):
    component = YosysComponent(circuit)
    component.create_from_netlist(_netlist(top, functional))
    return component


# --------------------------------------------------------------------------------------
# PortInOut
# --------------------------------------------------------------------------------------


def test_port_directions():
    """An inout port is an output and an input, and other ports are not inout"""
    circuit = Circuit()
    design = _design(circuit, "inout_port")
    assert isinstance(design.pad, PortInOut)
    assert design.pad.is_inout()
    assert design.pad.is_output()
    assert design.pad.is_input()
    assert design.pad.width == 4
    assert not design.a.is_inout()
    assert not design.y.is_inout()
    assert design.pad in design.outports()


def test_connect_to_itself():
    """A port can't drive itself"""
    circuit = Circuit()
    design = _design(circuit, "inout_port")
    with pytest.raises(PortConnectionError):
        design.pad.wire = design.pad


def test_nets_of_an_inout_port():
    """The inout port drives its nets, the tristate cells on them drive the port"""
    module = next(iter(_netlist("inout_port").get_modules().values()))
    nets = module.get_nets()
    for bit, net in enumerate(module.ports["pad"].bits):
        assert nets.source[net].name == "pad"
        assert nets.source[net].cell is None
        assert nets.source[net].bit_index == bit
        (driver,) = nets.inout_drivers[net]
        assert module.cells[driver.cell].type == "$_TBUF_"
        assert driver.name == "Y"


# --------------------------------------------------------------------------------------
# Inout ports of Verilog designs
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("functional", [False, True])
def test_drive_and_read(functional):
    """
    The design drives the port while oe is high, and reads what is on the wire: its own
    value, the value of the testbench, or "X" if both drive different values
    """
    circuit = Circuit()
    design = _design(circuit, "inout_port", functional)
    circuit.init()
    assert design.pad.is_tristate()
    design.a.value = 9
    for oe, testbench, drives, reads in [
        (1, "Z", 9, 9),
        (0, "Z", "Z", "Z"),
        (0, 6, "Z", 6),
        (1, 6, 9, "X"),
        (1, 9, 9, 9),
        (0, 0xF, "Z", 0xF),
        ("X", "Z", "X", "X"),
        (1, "Z", 9, 9),
    ]:
        design.oe.value = oe
        design.pad.value = testbench
        circuit.run(ns=100)
        assert design.pad.value == drives, (oe, testbench)
        assert design.pad.read_value() == reads, (oe, testbench)
        assert design.y.value == reads, (oe, testbench)


@pytest.mark.parametrize("functional", [False, True])
def test_unconnected_port_reads_its_own_value(functional):
    """Without other drivers the design reads what it drives, "Z" when it doesn't"""
    circuit = Circuit()
    design = _design(circuit, "inout_port", functional)
    circuit.init()
    design.a.value = 5
    design.oe.value = 1
    circuit.run(ns=100)
    assert design.y.value == 5
    design.oe.value = 0
    circuit.run(ns=100)
    assert design.y.value == "Z"


@pytest.mark.parametrize("functional", [False, True])
def test_bits_driven_one_by_one(functional):
    """
    Each bit is resolved with the bit of the wire. A word of which only some bits are
    driven is "X" for the ports it drives.
    """
    circuit = Circuit()
    design = _design(circuit, "inout_bits", functional)
    circuit.init()
    design.a.value = 0b0101
    design.oe.value = 0b0011
    design.pad.value = "Z"
    circuit.run(ns=100)
    assert design.pad.value == "X"
    assert design.y.value == "X"
    # The testbench drives the other bits, and the same values on the driven ones
    design.pad.value = 0b1101
    circuit.run(ns=100)
    assert design.y.value == 0b1101
    # A bit with another value
    design.pad.value = 0b1110
    circuit.run(ns=100)
    assert design.y.value == "X"
    assert [design.pad.get_bit(bit).value for bit in range(4)] == ["X", "X", 1, 1]
    design.oe.value = 0
    circuit.run(ns=100)
    assert design.pad.value == "Z"
    assert design.y.value == 0b1110


@pytest.mark.parametrize("functional", [False, True])
def test_port_that_is_only_read(functional):
    """A port that the design never drives is "Z" from the start, also on its wires"""
    circuit = Circuit()
    design = _design(circuit, "inout_read", functional)
    sink = Bus2Wires(circuit, "sink", width=8)
    design.pad.wire = sink.bus
    circuit.init()
    assert design.pad.is_tristate()
    assert design.pad.value == "Z"
    assert sink.bus.value == "Z"
    design.pad.value = 0x0F
    circuit.run(ns=100)
    assert design.y.value == 0xF0
    assert design.pad.value == "Z"


@pytest.mark.parametrize("functional", [False, True])
def test_constant_bits(functional):
    """An inout port of one bit, and one that is driven with constants"""
    circuit = Circuit()
    design = _design(circuit, "inout_constant", functional)
    circuit.init()
    assert design.pad.width == 1
    assert design.fixed.value == 0b10
    assert not design.fixed.is_tristate()
    design.a.value = 1
    design.oe.value = 1
    circuit.run(ns=100)
    assert design.pad.value == 1
    assert design.y.value == 1
    design.oe.value = 0
    design.pad.value = 0
    circuit.run(ns=100)
    assert design.pad.value == "Z"
    assert design.y.value == 0


class _SharedBus:
    """Two designs and a tristate buffer on one bus, and a sink that shows the bus"""

    def __init__(self, functional=False):
        self.circuit = Circuit()
        self.designs = [_design(self.circuit, "inout_port", functional) for _ in range(2)]
        self.buffer = TristateBuffer(self.circuit, "buffer", width=4)
        self.sink = Bus2Wires(self.circuit, "sink", width=4)
        first, second = (design.pad for design in self.designs)
        first.wire = second
        second.wire = first
        for port in (first, second, self.buffer.Y):
            port.wire = self.sink.bus
        self.buffer.Y.wire = first
        self.buffer.Y.wire = second
        self.circuit.init()
        for number, design in enumerate(self.designs):
            design.a.value = number + 1
        self.buffer.A.value = 8

    def drive(self, oe0, oe1, buffer_oe):
        self.designs[0].oe.value = oe0
        self.designs[1].oe.value = oe1
        self.buffer.OE.value = buffer_oe
        self.circuit.run(ns=100)
        return [design.y.value for design in self.designs], self.sink.bus.value


@pytest.mark.parametrize("functional", [False, True])
def test_designs_share_a_bus(functional):
    """Two designs drive each other's inout ports, and a tristate buffer drives both"""
    bus = _SharedBus(functional)
    assert bus.drive(0, 0, 0) == (["Z", "Z"], "Z")
    assert bus.drive(1, 0, 0) == ([1, 1], 1)
    assert bus.drive(0, 1, 0) == ([2, 2], 2)
    assert bus.drive(0, 0, 1) == ([8, 8], 8)
    assert bus.drive(1, 1, 0) == (["X", "X"], "X")
    assert bus.drive(0, 1, 1) == (["X", "X"], "X")
    # Not driven any more: no value is kept on the bus
    assert bus.drive(0, 0, 0) == (["Z", "Z"], "Z")


def test_delete_a_design_on_the_bus():
    """The design that is left reads the bus without the deleted one"""
    bus = _SharedBus()
    assert bus.drive(1, 0, 0) == ([1, 1], 1)
    bus.circuit.delete_component(bus.designs[0])
    bus.circuit.run(ns=100)
    assert bus.designs[1].pad.get_drivers() == [bus.buffer.Y]
    assert bus.designs[1].y.value == "Z"
    bus.buffer.OE.value = 1
    bus.circuit.run(ns=100)
    assert bus.designs[1].y.value == 8


def test_disconnect_the_last_driver():
    """Without other drivers, the design reads the wire as not driven by others"""
    circuit = Circuit()
    design = _design(circuit, "inout_port")
    value = StaticValue(circuit, "value", width=4, value=3)
    value.O.wire = design.pad
    circuit.init()
    design.oe.value = 0
    circuit.run(ns=100)
    assert design.y.value == 3
    value.O.disconnect(design.pad)
    circuit.run(ns=100)
    assert design.y.value == "Z"


def test_vcd(tmp_path):
    """The inout port is in the VCD file with what it drives"""
    vcd = tmp_path / "inout.vcd"
    circuit = Circuit(vcd=str(vcd))
    design = _design(circuit, "inout_port")
    circuit.init()
    design.a.value = 0b1010
    design.oe.value = 1
    circuit.run(ns=100)
    design.oe.value = 0
    circuit.run(ns=100)
    circuit.vcd_close()
    text = vcd.read_text()
    pad_id = next(line.split()[3] for line in text.splitlines() if line.endswith(" pad $end"))
    # The last value at each time: the bits change one by one, at the same time
    values = {}
    time = None
    for line in text.splitlines():
        if line.startswith("#"):
            time = int(line[1:])
        elif line.endswith(f" {pad_id}"):
            values[time] = line.split()[0]
    assert list(values.values())[-2:] == ["b1010", "bZ"]


def test_save_and_load(tmp_path):
    """The wires both ways between inout ports are saved, and loaded again"""
    circuit = Circuit(name="bus")
    designs = [YosysComponent(circuit, BUS_REGISTER) for _ in range(2)]
    designs[0].data.wire = designs[1].data
    designs[1].data.wire = designs[0].data
    path = tmp_path / "bus.json"
    circuit.to_json_file(path)
    loaded = Circuit()
    loaded.from_json_file(path)
    first = loaded.get_component("bus_register")
    second = loaded.get_component("bus_register_1")
    assert first.data.get_drivers() == [second.data]
    assert second.data.get_drivers() == [first.data]


def test_reload_with_inout_ports():
    """A design is built again from a netlist with the same ports"""
    circuit = Circuit()
    design = _design(circuit, "inout_port")
    sink = Bus2Wires(circuit, "sink", width=4)
    design.pad.wire = sink.bus
    design.reload_from_netlist(_netlist("inout_port", functional=True))
    circuit.init()
    design.a.value = 7
    design.oe.value = 1
    circuit.run(ns=100)
    assert sink.bus.value == 7
    assert design.y.value == 7
    # An inout port that would be an input
    with pytest.raises(YosysComponentException):
        design.reload_from_netlist(_netlist("inout_bits"))


class _BusRegister:
    """A testbench for examples/yosys_inout/bus_register.v"""

    def __init__(self, width, functional):
        self.circuit = Circuit()
        self.dut = YosysComponent(
            self.circuit, BUS_REGISTER, functional=functional, parameters={"WIDTH": width}
        )
        self.circuit.init()
        for port in (self.dut.clk, self.dut.we, self.dut.oe):
            port.value = 0
        self.circuit.run(ns=10)

    def clock(self):
        for value in (1, 0):
            self.dut.clk.value = value
            self.circuit.run(ns=10)

    def write(self, value):
        self.dut.data.value = value
        self.dut.we.value = 1
        self.clock()
        self.dut.we.value = 0
        self.dut.data.value = "Z"
        self.circuit.run(ns=10)

    def read(self):
        self.dut.oe.value = 1
        self.circuit.run(ns=10)
        value = self.dut.data.value
        self.dut.oe.value = 0
        self.circuit.run(ns=10)
        return value


@pytest.mark.parametrize("functional", [False, True])
@pytest.mark.parametrize("width", [1, 8, 16])
def test_bus_register(width, functional):
    """The example's register stores the value on the bus and drives it on the bus"""
    register = _BusRegister(width, functional)
    assert register.dut.data.width == width
    for value in (0, (1 << width) - 1, 0x5A5A & ((1 << width) - 1)):
        register.write(value)
        assert register.dut.value.value == value
        assert register.dut.data.value == "Z"
        assert register.read() == value


def test_walkie_talkie_circuit():
    """
    The GUI example: whichever walkie-talkie talks, both hear its message over the bus.
    Two that talk at once with different messages collide.
    """
    circuit = Circuit()
    circuit.from_json_file(WALKIE_TALKIE)
    talkies = [circuit.get_component(name) for name in ("walkie_talkie", "walkie_talkie_1")]
    switches = [circuit.get_component(name) for name in ("DipSwitch", "DipSwitch_1")]
    talks = [circuit.get_component(name) for name in ("PushButton", "PushButton_1")]
    assert all(isinstance(switch, DipSwitch) for switch in switches)
    assert all(isinstance(talk, PushButton) for talk in talks)
    assert talkies[0].bus.get_drivers() == [talkies[1].bus]
    assert talkies[1].bus.get_drivers() == [talkies[0].bus]
    circuit.init()
    for switch, bits in zip(switches, ((0, 2), (1, 3)), strict=True):
        for bit in bits:
            switch.select(bit)
            switch.onpress()
    for pressed, expected in [((), "Z"), ((0,), 0b0101), ((1,), 0b1010), ((0, 1), "X")]:
        for number, talk in enumerate(talks):
            if number in pressed:
                talk.push()
            else:
                talk.release()
        circuit.run(ms=1)
        assert [talkie.heard.value for talkie in talkies] == [expected, expected], pressed
