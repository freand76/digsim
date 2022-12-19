from circuit import Circuit


def led_callback(name, on):
    if on:
        print(f"LED: '{name}' is ON")
    else:
        print(f"LED: '{name}' is OFF")


circuit = Circuit(vcd="circuit.vcd")
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

circuit.time_increase(ms=10)
print("------------ 10")
button1.push()
circuit.time_increase(ms=10)
print("------------ 00")
button1.release()
circuit.time_increase(ms=10)
print("------------ 10")
button1.push()
circuit.time_increase(ms=10)
print("------------ 11")
button2.push()
circuit.time_increase(ms=10)
button1.release()
button2.release()
