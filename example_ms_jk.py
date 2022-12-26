from digsim import JK_MS, Circuit, Led, PushButton


def led_callback(comp):
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name
    if led_port.intval == 1:
        print(f"{time_ns:9}:LED: '{name}' is ON")
    else:
        print(f"{time_ns:9}:LED: '{name}' is OFF")


print("\n===================== Master Slave JK ==========================\n")
circuit = Circuit(vcd="ms_jk.vcd")
jk = JK_MS(circuit)
led = Led(circuit)
led.set_callback(led_callback)
clk = PushButton(circuit, "clk")
j = PushButton(circuit, "J")
k = PushButton(circuit, "K")
clk.O.wire = jk.C
j.O.wire = jk.J
k.O.wire = jk.K
jk.Q.wire = led.I
circuit.init()
k.push()
clk.push()
circuit.run(ms=1)
clk.release()
circuit.run(ms=1)

print("-- Set J --")
k.release()
j.push()

for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
    j.release()

print("-- Set K --")
k.push()

for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
    k.release()

print("-- Set KJ --")
k.push()
j.push()

for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
