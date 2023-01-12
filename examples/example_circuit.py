# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

import os

from digsim import Circuit


def led_callback(comp):
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name
    if led_port.intval == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


circuit = Circuit(vcd="circuit.vcd")
circuit.from_json_file(f"{os.path.dirname(__file__)}/example_circuit.json")
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
while circuit.process_single_event():
    pass
circuit.run_until(ms=10)
print("------------ 00")
button1.release()
while circuit.process_single_event():
    pass
circuit.run_until(ms=15)
print("------------ 10")
button1.push()
while circuit.process_single_event():
    pass
circuit.run_until(ms=20)
print("------------ 11")
button2.push()
while circuit.process_single_event():
    pass
