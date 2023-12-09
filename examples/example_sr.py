# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Basic example with two PushButtons connected to an SR component
The example will generate a gtkwave file, 'sr.vcd'.
"""

from digsim.circuit import Circuit
from digsim.circuit.components import SR, Led, PushButton


def led_callback(comp):
    """Callback function for LED component change"""

    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name()
    if led_port.value == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


circuit = Circuit(vcd="sr.vcd")
BS = PushButton(circuit, "S-Button")
BR = PushButton(circuit, "R-Button")
SR = SR(circuit)
D1 = Led(circuit, "D1", callback=led_callback)
BS.O.wire = SR.S
BR.O.wire = SR.R
SR.Q.wire = D1.I
circuit.init()
circuit.run(ms=10)

print("Reset")
BR.push()
circuit.run(ms=10)
BR.release()
circuit.run(ms=10)
print("Set")
BS.push()
circuit.run(ms=10)
BS.release()
circuit.run(ms=10)
print("Set (again)")
BS.push()
circuit.run(ms=10)
BS.release()
print("Reset")
BR.push()
circuit.run(ms=10)
BR.release()

circuit.vcd_close()
