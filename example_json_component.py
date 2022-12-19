from circuit import Circuit
from components import JsonComponent, Led, PushButton


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


circuit = Circuit(vcd="counter.vcd")
json_component = JsonComponent(circuit, "json_modules/counter.json")
clk = PushButton(circuit, "clk")
reset = PushButton(circuit, "reset")
up = PushButton(circuit, "up")
clk.port("O").connect(json_component.port("clk"))
reset.port("O").connect(json_component.port("reset"))
up.port("O").connect(json_component.port("up"))
circuit.init()

for port in circuit.get_port_paths():
    print("APA", port)

circuit.time_increase(ms=10)
up.push()
reset.push()
circuit.time_increase(ms=10)
reset.release()
circuit.time_increase(ms=10)

print("\n===================== Reset ==========================\n")

print(
    "OUT",
    json_component.port("cnt3").val,
    json_component.port("cnt2").val,
    json_component.port("cnt1").val,
    json_component.port("cnt0").val,
)


print("\n===================== Start ==========================\n")

for _ in range(0, 16):
    clk.push()
    circuit.time_increase(ms=10)
    clk.release()
    circuit.time_increase(ms=10)
    print(
        "OUT",
        json_component.port("cnt3").val,
        json_component.port("cnt2").val,
        json_component.port("cnt1").val,
        json_component.port("cnt0").val,
    )
