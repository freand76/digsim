# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test wires with several drivers, tristate outputs and high impedance ("Z")"""

from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import (
    AND,
    Bus2Wires,
    Led,
    PortConnectionError,
    PushButton,
    StaticValue,
    TristateBuffer,
    Wires2Bus,
    YosysComponent,
)
from digsim.circuit.components.atoms._port import resolve
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


@pytest.mark.parametrize(
    "values, expected",
    [
        ([], "Z"),
        (["Z", "Z"], "Z"),
        ([1, "Z"], 1),
        (["Z", 0, "Z"], 0),
        ([1, 1], 1),
        ([1, 0], "X"),
        (["X", "Z"], "X"),
        ([5, "Z", 5], 5),
        ([5, 6], "X"),
        ([1, "X"], "X"),
        (["X", 1, 1], "X"),
        ([0, 0, "Z"], 0),
        ([3, "Z", "Z"], 3),
    ],
)
def test_resolve(values, expected):
    """
    The driven value, "Z" if none drives, "X" for different values (contention) or when
    one of them drives "X"
    """
    assert resolve(values) == expected


class SharedWire:
    """Two tristate buffers with constant inputs, driving the same LED"""

    def __init__(self, width=1):
        self.circuit = Circuit(name="shared")
        self.values = [StaticValue(self.circuit, f"V{i}", width=width) for i in range(2)]
        self.enables = [PushButton(self.circuit, f"E{i}") for i in range(2)]
        self.buffers = [TristateBuffer(self.circuit, f"T{i}", width=width) for i in range(2)]
        self.wire = (
            Bus2Wires(self.circuit, "wire", width=width) if width > 1 else Led(self.circuit)
        )
        self.sink = self.wire.bus if width > 1 else self.wire.I
        for value, enable, buffer in zip(self.values, self.enables, self.buffers, strict=True):
            value.O.wire = buffer.A
            enable.O.wire = buffer.OE
            buffer.Y.wire = self.sink
        self.circuit.init()

    def drive(self, value0, enable0, value1, enable1):
        for value, number in zip(self.values, (value0, value1), strict=True):
            value.parameter_set("value", number)
            value.default_state()
        for enable, on in zip(self.enables, (enable0, enable1), strict=True):
            if on:
                enable.push()
            else:
                enable.release()
        self.circuit.run(ns=10)
        return self.sink.value


def test_shared_wire():
    """The enabled buffer drives the wire, none gives "Z", both with different values "X\""""
    wire = SharedWire()
    assert len(wire.sink.get_drivers()) == 2
    assert wire.drive(1, True, 0, False) == 1
    assert wire.drive(1, False, 0, True) == 0
    assert wire.drive(1, False, 0, False) == "Z"
    assert wire.drive(1, True, 0, True) == "X"
    assert wire.drive(1, True, 1, True) == 1


def test_shared_bus():
    """A bus driven by two buffers, and its bits"""
    wire = SharedWire(width=8)
    assert wire.drive(0xA5, True, 0x3C, False) == 0xA5
    assert wire.wire.bus_0.value == 1
    assert wire.drive(0xA5, False, 0x3C, True) == 0x3C
    assert wire.drive(0xA5, False, 0x3C, False) == "Z"
    # Not driven: none of the bits is
    assert wire.wire.bus_0.value == "Z"
    assert wire.drive(0xA5, True, 0x3C, True) == "X"


def test_any_outputs_share_a_wire():
    """Any outputs can drive the same input, but an output only once"""
    circuit = Circuit()
    led = Led(circuit)
    button = PushButton(circuit)
    buffer = TristateBuffer(circuit)
    second = PushButton(circuit, "second")
    button.O.wire = led.I
    buffer.Y.wire = led.I
    second.O.wire = led.I
    assert led.I.get_drivers() == [button.O, buffer.Y, second.O]
    assert led.I.can_add_wire()
    with pytest.raises(PortConnectionError, match="already connected"):
        button.O.wire = led.I
    with pytest.raises(PortConnectionError, match="different widths"):
        StaticValue(circuit, "bus", width=4).O.wire = led.I


class Buttons:
    """Push buttons (or other outputs) that drive the same LED"""

    def __init__(self, count=2):
        self.circuit = Circuit(name="buttons")
        self.led = Led(self.circuit)
        self.buttons = [PushButton(self.circuit, f"B{i}") for i in range(count)]
        for button in self.buttons:
            button.O.wire = self.led.I
        self.circuit.init()

    def press(self, *pressed):
        for button, down in zip(self.buttons, pressed, strict=True):
            if down:
                button.push()
            else:
                button.release()
        self.circuit.run(ns=10)
        return self.led.I.value


def test_outputs_drive_the_same_value():
    """Outputs that drive the same value give that value, different values give "X\""""
    buttons = Buttons()
    assert buttons.press(False, False) == 0
    assert buttons.press(True, True) == 1
    assert buttons.press(True, False) == "X"
    assert buttons.press(False, True) == "X"
    assert buttons.press(False, False) == 0


def test_three_outputs():
    """One output that drives another value than the others is enough for "X\""""
    buttons = Buttons(3)
    assert buttons.press(True, True, True) == 1
    assert buttons.press(True, True, False) == "X"
    assert buttons.press(False, False, False) == 0


def test_value_and_high_impedance():
    """A value and drivers that don't drive ("Z") give the value"""
    circuit = Circuit()
    led = Led(circuit)
    button = PushButton(circuit)
    enable = PushButton(circuit, "enable")
    value = StaticValue(circuit, "value", value=0)
    buffers = [TristateBuffer(circuit, f"T{i}") for i in range(2)]
    button.O.wire = led.I
    for buffer in buffers:
        enable.O.wire = buffer.OE
        value.O.wire = buffer.A
        buffer.Y.wire = led.I
    circuit.init()
    circuit.run(ns=10)
    assert [buffer.Y.value for buffer in buffers] == ["Z", "Z"]
    assert led.I.value == 0
    button.push()
    circuit.run(ns=10)
    assert led.I.value == 1
    # The buffers drive 0 too
    enable.push()
    circuit.run(ns=10)
    assert led.I.value == "X"
    button.release()
    circuit.run(ns=10)
    assert led.I.value == 0


def test_undefined_and_a_value():
    """An output that drives "X" makes the wire "X", whatever the others drive"""
    circuit = Circuit()
    led = Led(circuit)
    button = PushButton(circuit)
    # Its input isn't driven, so its output is undefined
    gate = AND(circuit)
    StaticValue(circuit, "one", value=1).O.wire = gate.B
    button.O.wire = led.I
    gate.Y.wire = led.I
    circuit.init()
    for pressed in (False, True):
        if pressed:
            button.push()
        circuit.run(ns=10)
        assert gate.Y.value == "X"
        assert led.I.value == "X"


def test_shared_bus_of_any_outputs():
    """A bus driven by two static values, and its bits"""
    circuit = Circuit()
    values = [StaticValue(circuit, f"V{i}", width=8, value=0xA5) for i in range(2)]
    bus = Bus2Wires(circuit, width=8)
    for value in values:
        value.O.wire = bus.bus
    circuit.init()
    circuit.run(ns=10)
    assert bus.bus.value == 0xA5
    assert bus.bus_0.value == 1
    values[1].parameter_set("value", 0x3C)
    values[1].default_state()
    circuit.run(ns=10)
    assert bus.bus.value == "X"


def test_disconnect_one_driver():
    """When one driver is disconnected, the other still drives the wire"""
    wire = SharedWire()
    first, second = (buffer.Y for buffer in wire.buffers)
    assert wire.drive(1, True, 0, False) == 1
    first.disconnect(wire.sink)
    assert wire.sink.get_drivers() == [second]
    assert wire.sink.get_driver() is second
    wire.circuit.run(ns=10)
    assert wire.sink.value == "Z"
    assert wire.drive(1, True, 0, True) == 0
    second.remove_wires()
    assert wire.sink.get_drivers() == []
    assert not wire.sink.has_driver()
    assert wire.sink.value == "X"


def test_new_drivers_after_the_shared_ones():
    """After its drivers are removed, an input takes new ones, one or several"""
    wire = SharedWire()
    for buffer in wire.buffers:
        buffer.Y.disconnect(wire.sink)
    button = PushButton(wire.circuit, "button")
    button.O.wire = wire.sink
    assert wire.sink.get_drivers() == [button.O]
    other = PushButton(wire.circuit, "other")
    other.O.wire = wire.sink
    assert wire.sink.get_drivers() == [button.O, other.O]
    wire.circuit.init()
    button.push()
    wire.circuit.run(ns=10)
    assert wire.sink.value == "X"
    button.O.disconnect(wire.sink)
    wire.circuit.run(ns=10)
    assert wire.sink.get_drivers() == [other.O]
    assert wire.sink.value == 0


def test_delete_a_driving_component():
    """Deleting one of the buffers keeps the other connected"""
    wire = SharedWire()
    wire.circuit.delete_component(wire.buffers[0])
    assert wire.sink.get_drivers() == [wire.buffers[1].Y]
    assert wire.drive(1, True, 1, True) == 1


@pytest.mark.parametrize("other, expected", [(0, 0), (1, "X")])
def test_z_through_a_gate(other, expected):
    """A gate input that is not driven is undefined, unless the other input decides"""
    circuit = Circuit()
    buffer = TristateBuffer(circuit)
    enable = PushButton(circuit, "enable")
    value = StaticValue(circuit, "value", value=other)
    gate = AND(circuit)
    enable.O.wire = buffer.OE
    buffer.Y.wire = gate.A
    value.O.wire = gate.B
    circuit.init()
    circuit.run(ns=10)
    assert gate.A.value == "Z"
    assert gate.Y.value == expected


def test_buffer_enable():
    """Active high or low enable, and an undefined enable gives "X\""""
    for active_low in (False, True):
        circuit = Circuit()
        buffer = TristateBuffer(circuit, width=4, active_low=active_low)
        circuit.init()
        buffer.A.value = 9
        buffer.OE.value = 0 if active_low else 1
        circuit.run(ns=10)
        assert buffer.Y.value == 9
        buffer.OE.value = 1 if active_low else 0
        circuit.run(ns=10)
        assert buffer.Y.value == "Z"
        buffer.OE.value = "X"
        circuit.run(ns=10)
        assert buffer.Y.value == "X"


def test_bus_from_bits():
    """A bus is "Z" when no bit is driven, and "X" when only some are"""
    circuit = Circuit()
    bus = Wires2Bus(circuit, width=2)
    buffers = [TristateBuffer(circuit, f"T{i}") for i in range(2)]
    for index, buffer in enumerate(buffers):
        buffer.Y.wire = bus.port(f"bus_{index}")
    circuit.init()
    circuit.run(ns=10)
    assert bus.bus.value == "Z"
    buffers[0].A.value = 1
    buffers[0].OE.value = 1
    circuit.run(ns=10)
    assert bus.bus.value == "X"
    buffers[1].A.value = 1
    buffers[1].OE.value = 1
    circuit.run(ns=10)
    assert bus.bus.value == 3


def test_vcd_high_impedance(tmp_path):
    """High impedance is written as "Z" to the VCD file"""
    vcd = tmp_path / "tristate.vcd"
    wire = SharedWire(width=8)
    wire.circuit.vcd(str(vcd))
    wire.circuit.init()
    wire.drive(0x55, True, 0, False)
    wire.drive(0x55, False, 0, False)
    wire.circuit.vcd_close()
    text = vcd.read_text()
    assert "bZ " in text
    assert "b1010101 " in text


def test_save_and_load_outputs_on_one_wire(tmp_path):
    """Push buttons on one LED are saved as two wires, and loaded again"""
    buttons = Buttons()
    path = tmp_path / "buttons.json"
    buttons.circuit.to_json_file(path)
    circuit = Circuit()
    circuit.from_json_file(path)
    led = circuit.get_component("Led")
    assert [driver.parent().name() for driver in led.I.get_drivers()] == ["B0", "B1"]


def test_save_and_load_shared_wire(tmp_path):
    """A wire with two drivers is saved as two wires, and loaded again"""
    wire = SharedWire()
    path = tmp_path / "shared.json"
    wire.circuit.to_json_file(path)
    circuit = Circuit()
    circuit.from_json_file(path)
    led = circuit.get_component("Led")
    assert [driver.parent().name() for driver in led.I.get_drivers()] == ["T0", "T1"]


# --------------------------------------------------------------------------------------
# Tristate outputs of Verilog designs
# --------------------------------------------------------------------------------------

VERILOG = Path(__file__).parent / "verilog" / "tristate.v"


def _design(circuit, top, functional):
    synthesis = Synthesis([str(VERILOG)], top, functional=functional)
    component = YosysComponent(circuit)
    component.create_from_netlist(YosysNetlist(**synthesis.synth_to_dict(silent=True)))
    return component


@pytest.mark.parametrize("functional", [False, True])
def test_verilog_tristate_output(functional):
    """assign y = oe ? a : 'bz: the output is not driven when oe is low"""
    circuit = Circuit()
    design = _design(circuit, "tristate_output", functional)
    circuit.init()
    assert design.y.is_tristate()
    design.a.value = 9
    for oe, expected in [(1, 9), (0, "Z"), (1, 9), ("X", "X"), (0, "Z")]:
        design.oe.value = oe
        circuit.run(ns=100)
        assert design.y.value == expected, oe


@pytest.mark.parametrize("functional", [False, True])
def test_verilog_tristate_bus(functional):
    """Two tristate drivers on a bus inside a design, with the bus as the output"""
    circuit = Circuit()
    design = _design(circuit, "tristate_bus", functional)
    circuit.init()
    design.a.value = 3
    design.b.value = 12
    for oe_a, oe_b, expected in [(1, 0, 3), (0, 1, 12), (0, 0, "Z"), (1, 0, 3)]:
        design.oe_a.value = oe_a
        design.oe_b.value = oe_b
        circuit.run(ns=100)
        assert design.y.value == expected, (oe_a, oe_b)


@pytest.mark.parametrize("functional", [False, True])
def test_verilog_outputs_share_a_wire(functional):
    """The tristate outputs of two designs drive the same bus"""
    circuit = Circuit()
    designs = [_design(circuit, "tristate_output", functional) for i in range(2)]
    bus = Bus2Wires(circuit, "bus", width=4)
    for design in designs:
        design.y.wire = bus.bus
    circuit.init()
    designs[0].a.value = 5
    designs[1].a.value = 10
    for oe0, oe1, expected in [(1, 0, 5), (0, 1, 10), (0, 0, "Z"), (1, 1, "X")]:
        designs[0].oe.value = oe0
        designs[1].oe.value = oe1
        circuit.run(ns=100)
        assert bus.bus.value == expected, (oe0, oe1)
