from components import Led, PushButton
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
OS.push_release()
OS.push_release()
OR.push_release()
OR.push_release()
OS.push_release()
OR.push_release()
