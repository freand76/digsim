# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the VCD (waves) output"""

from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton


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
