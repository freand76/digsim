from circuit import Circuit
from components import Led, PushButton
from components.gates import SR


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


circuit = Circuit(vcd="sr.vcd")
BS = PushButton(circuit, "S-Button", inverted=True)
BR = PushButton(circuit, "R-Button", inverted=True)
SR = SR(circuit)
D1 = Led(circuit, "D1", callback=led_callback)
BS.port("O").connect(SR.port("nS"))
BR.port("O").connect(SR.port("nR"))
SR.port("Q").connect(D1.port("I"))
circuit.init()
circuit.time_increase(ms=10)

print("Set")
BS.push()
circuit.time_increase(ms=10)
BS.release()
circuit.time_increase(ms=100)
print("Reset")
BR.push()
circuit.time_increase(ms=10)
BR.release()
circuit.time_increase(ms=100)
BS.push()
