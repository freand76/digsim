from digsim import VDD, Circuit, JsonComponent, PushButton

circuit = Circuit()
json_component = JsonComponent(circuit, "json_modules/counter.json")

clk = PushButton(circuit, "clk")
reset = PushButton(circuit, "reset")

vdd = VDD(circuit)
clk.O.wire = json_component.clk
reset.O.wire = json_component.reset
vdd.wire = json_component.up
circuit.init()


circuit.run(ms=10)
reset.push()
circuit.run(ms=10)
reset.release()
circuit.run(ms=10)

circuit.vcd("counter.vcd")

print("\n===================== Reset ==========================\n")

print(json_component)

print("\n===================== Start ==========================\n")

for _ in range(0, 16):
    clk.push()
    circuit.run(ms=10)
    clk.release()
    circuit.run(ms=10)
    print(
        "OUT",
        json_component.cnt3.bitval,
        json_component.cnt2.bitval,
        json_component.cnt1.bitval,
        json_component.cnt0.bitval,
    )
