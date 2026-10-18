# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Example with a state machine in SystemVerilog, a traffic light (traffic_light.sv).
Its states are a SystemVerilog enum, so the Yosys netlist has their names. The
component is created with signals=True: its internal signals, the state and the timer,
can be read with signal() and state(), and are written to the VCD file. The state is
written as text, the name of the state, which a waveform viewer like GTKWave shows.

The example prints each change of the state, and writes the waveforms to
traffic_light.vcd.
"""

import pathlib

from digsim.circuit import Circuit
from digsim.circuit.components import Clock, PushButton, YosysComponent


# Get the relative path to the example folder
example_path = pathlib.Path(__file__).parent.resolve().relative_to(pathlib.Path.cwd())

with Circuit(vcd="traffic_light.vcd") as circuit:
    clock = Clock(circuit, frequency=10, name="clk")
    reset = PushButton(circuit, "reset")
    request = PushButton(circuit, "request")
    light = YosysComponent(
        circuit, path=example_path / "traffic_light.sv", functional=True, signals=True
    )
    clock.O.wire = light.clk
    reset.O.wire = light.reset
    request.O.wire = light.request
    circuit.init()

    print("Internal signals:", ", ".join(light.signal_names()))

    def run_and_print(ms: int) -> None:
        """Run a while, and print the state each time it changes"""
        state = light.state("state")
        for _ in range(ms // 10):
            circuit.run(ms=10)
            if light.state("state") != state:
                state = light.state("state")
                print(f"{circuit.time_ns // 1_000_000:5} ms: {state}")

    # Reset, then a request: red, red and yellow, green, yellow and red again
    reset.push()
    run_and_print(200)
    reset.release()
    print(f"{circuit.time_ns // 1_000_000:5} ms: {light.state('state')} after the reset")
    request.push()
    run_and_print(200)
    request.release()
    run_and_print(1000)
