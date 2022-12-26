from digsim import AND, Circuit, Led, PushButton


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

    @property
    def circuit(self):
        return self._circuit
