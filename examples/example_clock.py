# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, Led


def led_callback(comp):
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name
    if led_port.intval == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


circuit = Circuit(vcd="clock.vcd")
clk = Clock(circuit, 20)
D1 = Led(circuit, "D1", callback=led_callback)
clk.wire = D1.I
circuit.init()
circuit.run(s=1)
