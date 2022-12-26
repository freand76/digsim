from digsim import AND, Circuit, Led, PushButton


def led_cb(time, name, on):
    if on:
        print(f"{time:9}:LED: '{name}' is ON")
    else:
        print(f"{time:9}:LED: '{name}' is OFF")


class AppModel:
    def __init__(self):
        self._circuit = Circuit()
        bu_a = PushButton(self._circuit, "ButtonA")
        bu_b = PushButton(self._circuit, "ButtonB")
        _and = AND(self._circuit)
        _led = Led(self._circuit, "D")
        bu_a.O.wire = _and.A
        bu_a.O.wire = _and.B
        _and.Y.wire = _led.I
        self._circuit.init()
        _led.set_callback(led_cb)

    @property
    def circuit(self):
        return self._circuit
