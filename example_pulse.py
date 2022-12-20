from circuit import Circuit
from components import Led, PushButton
from components.gates import AND, NOT


def led_callback(time, name, on):
    if on:
        print(f"{time:9}:LED: '{name}' is ON")
    else:
        print(f"{time:9}:LED: '{name}' is OFF")


circuit = Circuit(vcd="pulse.vcd")
B = PushButton(circuit, "Button")
_not1 = NOT(circuit, "not1")
_not2 = NOT(circuit, "not2")
_not3 = NOT(circuit, "not3")
_and = AND(circuit)
D1 = Led(circuit, "D1", callback=led_callback)
D2 = Led(circuit, "D2", callback=led_callback)
D3 = Led(circuit, "D3", callback=led_callback)
D4 = Led(circuit, "D4", callback=led_callback)

B.port("O").connect(_not1.port("A"))
B.port("O").connect(_and.port("A"))
_not1.port("Y").connect(_not2.port("A"))
_not2.port("Y").connect(_not3.port("A"))
_not3.port("Y").connect(_and.port("B"))
_not1.port("Y").connect(D1.port("I"))
_not2.port("Y").connect(D2.port("I"))
_not3.port("Y").connect(D3.port("I"))
_and.port("Y").connect(D4.port("I"))
circuit.init()

circuit.run(ms=10)
B.push()
circuit.run(ms=10)
B.release()
circuit.run(ms=10)

circuit.close()
