# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Basic example with a clock component connected to an LED component
The example will generate a gtkwave file, 'clock.vcd'.
"""

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, Led


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
circuit = Circuit(vcd="clock.vcd")

# Create a clock and an LED component
clk = Clock(circuit, frequency=20)
D1 = Led(circuit, "D1", callback=led_callback)

# Connect the clock to the LED
clk.wire = D1.I

# Initialize and run the simulation for 1 second
circuit.init()
circuit.run(s=1)
