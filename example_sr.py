from digsim import SR, Circuit, Led, PushButton


def led_callback(time, name, on):
    if on:
        print(f"{time:9}:LED: '{name}' is ON")
    else:
        print(f"{time:9}:LED: '{name}' is OFF")


circuit = Circuit(vcd="sr.vcd")
BS = PushButton(circuit, "S-Button", inverted=True)
BR = PushButton(circuit, "R-Button", inverted=True)
SR = SR(circuit)
D1 = Led(circuit, "D1", callback=led_callback)
BS.O.wire = SR.nS
BR.O.wire = SR.nR
SR.Q.wire = D1.I
circuit.init()
circuit.run(ms=10)

print("Reset")
BR.push()
circuit.run(ms=10)
BR.release()
circuit.run(ms=10)
print("Set")
BS.push()
circuit.run(ms=10)
BS.release()
circuit.run(ms=10)

BS.push()
circuit.vcd_close()
