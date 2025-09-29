# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Example that will create a circuit and store it as a json file.
The example will generate a json circuit file 'pulse_circuit.json'
and a gtkwave file, 'pulse.vcd'.
"""

import pathlib

from digsim.circuit import Circuit
from digsim.circuit.components import AND, NOT, Led, PushButton


def led_callback(comp):
    """Callback function for LED component change"""

    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name()
    if led_port.value == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


# Get the relative path to example folder
example_path = pathlib.Path(__file__).parent.relative_to(pathlib.Path.cwd())

# --- Create and run the first circuit ---
# Create a new circuit with VCD output
circuit = Circuit(name="example_pulse", vcd="pulse.vcd")

# Create components
B = PushButton(circuit, "Button")
_not1 = NOT(circuit, "not1")
_not2 = NOT(circuit, "not2")
_not3 = NOT(circuit, "not3")
_and = AND(circuit)
D = Led(circuit, "D", callback=led_callback)

# Connect the components
B.O.wire = _not1.A
B.O.wire = _and.A
_not1.Y.wire = _not2.A
_not2.Y.wire = _not3.A
_not3.Y.wire = _and.B
_and.Y.wire = D.I

# Initialize and run the simulation
circuit.init()
circuit.run(ms=10)

print("ON")
B.push()
circuit.run(ms=10)
print("OFF")
B.release()
circuit.run(ms=10)

# Close the VCD file and save the circuit to a JSON file
circuit.vcd_close()
circuit.to_json_file(example_path / "pulse_circuit.json")


# --- Load the circuit and run it again ---
# Create a new circuit
circuit2 = Circuit()

# Load the circuit from the JSON file
circuit2.from_json_file(example_path / "pulse_circuit.json")

# Get components from the loaded circuit
led = circuit2.get_component("D")
led.set_callback(led_callback)
button = circuit2.get_component("Button")

# Initialize and run the loaded circuit
circuit2.init()
circuit2.run(ms=5)
button.push()
circuit2.run(ms=5)
button.release()
circuit2.run(ms=5)
