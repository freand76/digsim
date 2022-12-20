from circuit import Circuit
from components import JsonComponent, Led, PushButton

circuit = Circuit(vcd="counter.vcd")
json_component = JsonComponent(circuit, "json_modules/counter.json")
clk = PushButton(circuit, "clk")
reset = PushButton(circuit, "reset")
up = PushButton(circuit, "up")
clk.port("O").connect(json_component.port("clk"))
reset.port("O").connect(json_component.port("reset"))
up.port("O").connect(json_component.port("up"))
circuit.init()

circuit.run(ms=10)
up.push()
reset.push()
circuit.run(ms=10)
reset.release()
circuit.run(ms=10)

print("\n===================== Reset ==========================\n")

print(
    "OUT",
    json_component.port("cnt3").bitval,
    json_component.port("cnt2").bitval,
    json_component.port("cnt1").bitval,
    json_component.port("cnt0").bitval,
)


print("\n===================== Start ==========================\n")

for _ in range(0, 16):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
    print(
        "OUT",
        json_component.port("cnt3").bitval,
        json_component.port("cnt2").bitval,
        json_component.port("cnt1").bitval,
        json_component.port("cnt0").bitval,
    )
