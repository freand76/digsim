from circuit import Circuit


def led_callback(time, name, on):
    if on:
        print(f"{time:9}:LED: '{name}' is ON")
    else:
        print(f"{time:9}:LED: '{name}' is OFF")


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

circuit.run(ms=10)
print("------------ 10")
button1.push()
circuit.run(ms=10)
print("------------ 00")
button1.release()
circuit.run(ms=10)
print("------------ 10")
button1.push()
circuit.run(ms=10)
print("------------ 11")
button2.push()
circuit.run(ms=10)
button1.release()
button2.release()
