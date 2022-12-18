from circuit import Circuit
from components import Led, PushButton
from components.gates import SR


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


circuit = Circuit()
BS = PushButton(circuit, "S Button", inverted=True)
BR = PushButton(circuit, "R Button", inverted=True)
SR = SR(circuit)
D1 = Led(circuit, "D1", callback=led_callback)
BS.outport("O").connect(SR.inport("nS"))
BR.outport("O").connect(SR.inport("nR"))
SR.outport("Q").connect(D1.inport("I"))
circuit.init()

print(SR.inports, SR.outports)
print("Set")
BS.push_release()
BS.push_release()
BS.push_release()
print("Reset")
BR.push_release()
BR.push_release()
BR.push_release()
BR.push_release()
