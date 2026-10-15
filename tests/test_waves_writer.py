# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the VCD (waves) output"""

from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton, Wires2Bus
from digsim.circuit.components._yosys_atoms import _NOT_


def _changes(vcd_text, scope, name):
    """Return the values written for a single-bit signal, in order"""
    ident = None
    current_scope = None
    values = []
    for line in vcd_text.splitlines():
        parts = line.split()
        if parts[:2] == ["$scope", "module"]:
            current_scope = parts[2]
        elif parts[:1] == ["$var"] and current_scope == scope and parts[4] == name:
            ident = parts[3]
        elif ident is not None and len(line) > 1 and line[1:] == ident and line[0] in "01x":
            values.append(line[0])
    return values


def test_vcd_follows_rewiring(tmp_path):
    """Connections made after the VCD started are written too"""
    vcd_path = tmp_path / "rewire.vcd"
    circuit = Circuit(vcd=str(vcd_path))
    button = PushButton(circuit, "button")
    led1 = Led(circuit, "led1")
    led2 = Led(circuit, "led2")
    button.O.wire = led1.I
    circuit.init()
    button.push()
    circuit.run(ms=1)
    button.release()
    circuit.run(ms=1)

    # Connect a second LED while the VCD output is active
    button.O.wire = led2.I
    button.push()
    circuit.run(ms=1)
    circuit.vcd_close()

    vcd_text = vcd_path.read_text()
    assert _changes(vcd_text, "led1", "I")[-3:] == ["1", "0", "1"]
    assert _changes(vcd_text, "led2", "I")[-1] == "1"


def _last_vcd_value(vcd_text, name):
    """The last value written for the variable 'name' in a VCD file"""
    ident = next(
        line.split()[3]
        for line in vcd_text.splitlines()
        if line.startswith("$var") and line.split()[4] == name
    )
    values = [
        line.split()[0]
        for line in vcd_text.split("$enddefinitions $end")[1].splitlines()
        if line.endswith(f" {ident}")
    ]
    return values[-1]


def test_bus_that_becomes_undefined(tmp_path):
    """When a bit of a bus becomes undefined, the VCD shows the bus as undefined"""
    vcd = tmp_path / "bus.vcd"
    circuit = Circuit(vcd=str(vcd))
    not_a = _NOT_(circuit, "not_a")
    not_b = _NOT_(circuit, "not_b")
    wires2bus = Wires2Bus(circuit, "wires2bus", width=2)
    not_a.Y.wire = wires2bus.port("bus_0")
    not_b.Y.wire = wires2bus.port("bus_1")
    circuit.init()
    not_a.A.value = 0
    not_b.A.value = 0
    circuit.run(ns=10)
    assert wires2bus.bus.value == 3
    not_b.A.value = "X"
    circuit.run(ns=10)
    assert wires2bus.bus.value == "X"
    circuit.vcd_close()
    assert _last_vcd_value(vcd.read_text(), "bus") == "bX"
