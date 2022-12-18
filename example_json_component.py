from circuit import Circuit
from components import JsonComponent, Led, PushButton


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


circuit = Circuit()
json_component = JsonComponent(circuit, "json_modules/counter.json")
clk = PushButton(circuit, "clk")
reset = PushButton(circuit, "reset")
up = PushButton(circuit, "up")
clk.outport("O").connect(json_component.inport("clk"))
reset.outport("O").connect(json_component.inport("reset"))
up.outport("O").connect(json_component.inport("up"))
circuit.init()
up.push()
reset.push_release()
x = json_component

print("\n===================== Reset ==========================\n")

print(
    "OUT",
    json_component.outport("cnt3").val,
    json_component.outport("cnt2").val,
    json_component.outport("cnt1").val,
    json_component.outport("cnt0").val,
)


print("\n===================== Start ==========================\n")

for _ in range(0, 16):
    clk.push_release()
    print(
        "OUT",
        json_component.outport("cnt3").val,
        json_component.outport("cnt2").val,
        json_component.outport("cnt1").val,
        json_component.outport("cnt0").val,
    )
