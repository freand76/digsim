from digsim import Circuit, Clock, Led


def led_callback(time, name, on):
    if on:
        print(f"{time:9}:LED: '{name}' is ON")
    else:
        print(f"{time:9}:LED: '{name}' is OFF")


circuit = Circuit(vcd="clock.vcd")
clk = Clock(circuit, 20)
D1 = Led(circuit, "D1", callback=led_callback)
clk.wire = D1.I
circuit.init()
circuit.run(s=1)
