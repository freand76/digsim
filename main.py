from circuit import Circuit
from components import JsonComponent, Led, PushButton
from components.gates import SR


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


OS = PushButton("S Button", inverted=True)
OR = PushButton("R Button", inverted=True)
SR = SR()
D1 = Led("D1", callback=led_callback)

OS.outport("O").connect(SR.inport("nS"))
OR.outport("O").connect(SR.inport("nR"))
SR.outport("Q").connect(D1.inport("I"))

OS.init()
OR.init()

print(SR.inports, SR.outports)
print("Set")
OS.push_release()
print("Reset")
OR.push_release()


json_component = JsonComponent("json_modules/counter.json")


clk = PushButton("clk")
reset = PushButton("reset")
up = PushButton("up")
clk.outport("O").connect(json_component.inport("clk"))
reset.outport("O").connect(json_component.inport("reset"))
up.outport("O").connect(json_component.inport("up"))
clk.init()
up.push()
reset.push_release()
x = json_component

print("\n===================== Reset ==========================\n")

print(
    "OUT",
    json_component.outport("cnt3"),
    json_component.outport("cnt2"),
    json_component.outport("cnt1"),
    json_component.outport("cnt0"),
)


print("\n===================== Start ==========================\n")

for _ in range(0, 16):
    clk.push_release()
    json_component.delta()
    print(
        "OUT",
        json_component.outport("cnt3"),
        json_component.outport("cnt2"),
        json_component.outport("cnt1"),
        json_component.outport("cnt0"),
    )


circuit = Circuit()
circuit.from_json_file("examples/example_circuit.json")
circuit.init()
led1 = circuit.get_component("and_led")
led2 = circuit.get_component("not_led")
led3 = circuit.get_component("xor_led")
led1.set_callback(led_callback)
led2.set_callback(led_callback)
led3.set_callback(led_callback)
button1 = circuit.get_component("button1")
button2 = circuit.get_component("button2")
print("------------ 10")
button1.push()
print("------------ 00")
button1.release()
print("------------ 10")
button1.push()
print("------------ 11")
button2.push()
