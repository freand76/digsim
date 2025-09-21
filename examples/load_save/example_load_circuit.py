# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Example that will load a previously stored circuit from a json file.
The example will generate a gtkwave file, 'circuit.vcd'.
"""

import pathlib

from digsim import Circuit


def led_callback(comp):
    """Callback function for LED component change"""
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name()
    if led_port.value == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


# Get the path to example folder
example_path = pathlib.Path(__file__).parent

circuit = Circuit(vcd="circuit.vcd")
circuit.from_json_file(example_path / "example_circuit.json")
circuit.init()
led1 = circuit.get_component("and_led")
led2 = circuit.get_component("not_led")
led3 = circuit.get_component("xor_led")
led1.set_callback(led_callback)
led2.set_callback(led_callback)
led3.set_callback(led_callback)
button1 = circuit.get_component("button1")
button2 = circuit.get_component("button2")

circuit.run_until(ms=5)
print("------------ 10")
button1.push()
circuit.run_until(ms=10)
print("------------ 00")
button1.release()
circuit.run_until(ms=15)
print("------------ 10")
button1.push()
circuit.run_until(ms=20)
print("------------ 11")
button2.push()
circuit.run_until(ms=25)
