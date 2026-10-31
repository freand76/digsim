# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Pytest module to test VDD and GND, a constant 1 and 0"""

from digsim.circuit import Circuit
from digsim.circuit.components import AND, GND, OR, VDD, Led


def test_vdd_and_gnd_drive_one_and_zero():
    circuit = Circuit()
    vdd = VDD(circuit)
    gnd = GND(circuit)
    and_gate = AND(circuit)
    or_gate = OR(circuit)
    led_and = Led(circuit)
    led_or = Led(circuit)
    vdd.O.wire = and_gate.A
    gnd.O.wire = and_gate.B
    vdd.O.wire = or_gate.A
    gnd.O.wire = or_gate.B
    and_gate.Y.wire = led_and.I
    or_gate.Y.wire = led_or.I
    circuit.init()
    circuit.run(ms=1)
    assert vdd.O.value == 1
    assert gnd.O.value == 0
    assert not led_and.active
    assert led_or.active


def test_vdd_and_gnd_are_saved_and_loaded(tmp_path):
    circuit = Circuit(name="levels")
    vdd = VDD(circuit)
    led = Led(circuit)
    vdd.O.wire = led.I
    path = tmp_path / "vdd.circuit"
    circuit.to_json_file(path)
    loaded = Circuit()
    loaded.from_json_file(path)
    names = {type(component).__name__ for component in loaded.get_toplevel_components()}
    assert names == {"VDD", "Led"}
    loaded.init()
    loaded.run(ms=1)
    (loaded_led,) = [c for c in loaded.get_toplevel_components() if isinstance(c, Led)]
    assert loaded_led.active
