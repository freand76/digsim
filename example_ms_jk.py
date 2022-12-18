from circuit import Circuit
from components import Led, PushButton
from components.gates import JK_MS


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


print("\n===================== Master Slave JK ==========================\n")
circuit = Circuit()
jk = JK_MS(circuit)
led = Led(circuit)
led.set_callback(led_callback)
clk = PushButton(circuit, "clk")
j = PushButton(circuit, "J")
k = PushButton(circuit, "K")
clk.outport("O").connect(jk.inport("C"))
j.outport("O").connect(jk.inport("J"))
k.outport("O").connect(jk.inport("K"))
jk.outport("Q").connect(led.inport("I"))
circuit.init()

j.release()
k.release()
clk.push_release(4)

print("-- Set K --")
k.push()
j.release()
clk.push_release(4)
print("-- Set J --")
k.release()
j.push()
clk.push_release(4)
print("-- Set KJ --")
k.push()
j.push()
clk.push_release(4)
