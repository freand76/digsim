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

    # Get the port and circuit time from the component
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name()

    # Print the LED state
    if led_port.value == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


# Create a new circuit with VCD output
circuit = Circuit(vcd="sr.vcd")

# Create components: two push buttons, an SR latch, and an LED
BS = PushButton(circuit, "S-Button")
BR = PushButton(circuit, "R-Button")
SR = SR(circuit)
D1 = Led(circuit, "D1", callback=led_callback)

# Connect the components
BS.O.wire = SR.S
BR.O.wire = SR.R
SR.Q.wire = D1.I

# Initialize the circuit and run for a short time
circuit.init()
circuit.run(ms=10)

# --- Test sequence ---
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

# Close the VCD file
circuit.vcd_close()
