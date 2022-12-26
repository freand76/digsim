from digsim import AND, Circuit, Led, OnOffSwitch


def comp_cb(comp):
    led_port = comp.ports[0]
    time_ns = comp.circuit.time_ns
    name = comp.name
    if led_port.intval == 1:
        print(f"{time_ns:9}: '{name}' is ON")
    else:
        print(f"{time_ns:9}: '{name}' is OFF")


class AppModel:
    def __init__(self):
        self._circuit = Circuit()
        _bu_a = OnOffSwitch(self._circuit, "SwitchA")
        _bu_b = OnOffSwitch(self._circuit, "SwitchB")
        _and = AND(self._circuit)
        _led = Led(self._circuit, "D")
        _bu_a.O.wire = _and.A
        _bu_b.O.wire = _and.B
        _and.Y.wire = _led.I
        _led.set_callback(comp_cb)
        _bu_a.set_callback(comp_cb)
        _bu_b.set_callback(comp_cb)
        self._circuit.init()

    @property
    def circuit(self):
        return self._circuit
