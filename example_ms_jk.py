from circuit import Circuit
from components import Led, PushButton
from components.gates import JK_MS


def led_callback(time, name, on):
    if on:
        print(f"{time:9}:LED: '{name}' is ON")
    else:
        print(f"{time:9}:LED: '{name}' is OFF")


print("\n===================== Master Slave JK ==========================\n")
circuit = Circuit(vcd="ms_jk.vcd")
jk = JK_MS(circuit)
led = Led(circuit)
led.set_callback(led_callback)
clk = PushButton(circuit, "clk")
j = PushButton(circuit, "J")
k = PushButton(circuit, "K")
clk.port("O").connect(jk.port("C"))
j.port("O").connect(jk.port("J"))
k.port("O").connect(jk.port("K"))
jk.port("Q").connect(led.port("I"))
circuit.init()

circuit.run(ms=10)
for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)

print("-- Set J --")
k.release()
j.push()

for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)

print("-- Set K --")
k.push()
j.release()

for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)

print("-- Set KJ --")
k.push()
j.push()

for _ in range(4):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
