# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the Circuit class"""

from digsim.circuit import Circuit
from digsim.circuit.components import AND, SR, Led, PushButton, YosysComponent


def test_delete_component():
    """A deleted component is removed from the circuit and disconnected"""
    circuit = Circuit()
    button = PushButton(circuit, "button")
    gate = AND(circuit, "gate")
    button.O.wire = gate.A
    circuit.delete_component(gate)
    assert [component.name() for component in circuit.components] == ["button"]
    assert button.O.wired_ports == []


def test_delete_multi_component():
    """Deleting a component built from other components removes them too"""
    circuit = Circuit()
    latch = SR(circuit, "latch")
    led = Led(circuit, "led")
    latch.Q.wire = led.I
    assert len(circuit.components) == 4  # the latch, its two NOR gates and the LED
    circuit.delete_component(latch)
    assert [component.name() for component in circuit.components] == ["led"]


def test_delete_yosys_component():
    """Deleting a Yosys component removes all its gates"""
    circuit = Circuit()
    counter = YosysComponent(circuit, path="examples/yosys_counter/counter.json")
    Led(circuit, "led")
    assert len(circuit.components) > 2
    circuit.delete_component(counter)
    assert [component.name() for component in circuit.components] == ["led"]


def test_context_manager_closes_vcd(tmp_path):
    """A circuit used in a with statement closes its VCD file at the end"""
    vcd_path = tmp_path / "with.vcd"
    with Circuit(vcd=str(vcd_path)) as circuit:
        button = PushButton(circuit, "button")
        circuit.init()
        button.push()
        circuit.run(ms=1)
    # Without closing, the VCD writer would still hold the values in its buffer
    assert "$dumpvars" in vcd_path.read_text()


def test_reload_yosys_component():
    """Reloading a Yosys component replaces its gates, and the counter still counts"""
    circuit = Circuit()
    counter = YosysComponent(circuit, path="examples/yosys_counter/counter.json")
    clock = PushButton(circuit, "clock")
    clock.O.wire = counter.clk
    component_count = len(circuit.components)
    counter.reload_file()
    assert len(circuit.components) == component_count

    circuit.init()
    counter.up.value = 1
    counter.reset.value = 1
    circuit.run(ms=1)
    counter.reset.value = 0
    circuit.run(ms=1)
    for expected in range(1, 4):
        clock.push()
        circuit.run(ms=1)
        clock.release()
        circuit.run(ms=1)
        assert counter.cnt.value == expected
