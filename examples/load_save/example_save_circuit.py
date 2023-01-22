# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from digsim.circuit import Circuit
from digsim.circuit.components import AND, NOT, Led, PushButton


def led_callback(comp):
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name()
    if led_port.value == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


circuit = Circuit(name="example_pulse", vcd="pulse.vcd")
B = PushButton(circuit, "Button")
_not1 = NOT(circuit, "not1")
_not2 = NOT(circuit, "not2")
_not3 = NOT(circuit, "not3")
_and = AND(circuit)
D = Led(circuit, "D", callback=led_callback)

B.O.wire = _not1.A
B.O.wire = _and.A
_not1.Y.wire = _not2.A
_not2.Y.wire = _not3.A
_not3.Y.wire = _and.B
_and.Y.wire = D.I
circuit.init()
circuit.run(ms=10)

print("ON")
B.push()
circuit.run(ms=10)
print("OFF")
B.release()
circuit.run(ms=10)

circuit.vcd_close()
circuit.to_json_file("pulse_circuit.json")

circuit2 = Circuit()
circuit2.from_json_file("pulse_circuit.json")
led = circuit2.get_component("D")
led.set_callback(led_callback)
button = circuit2.get_component("Button")
circuit2.init()
circuit2.run(ms=5)
button.push()
circuit2.run(ms=5)
button.release()
circuit2.run(ms=5)
