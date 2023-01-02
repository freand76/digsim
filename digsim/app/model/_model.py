from functools import partial

from PySide6.QtCore import QObject, QPoint, Signal

from digsim import AND, Circuit, Component, Led, OnOffSwitch


class AppModel(QObject):

    sig_notify = Signal(Component)

    def __init__(self):
        super().__init__()
        self._component_position = {}
        self._circuit = Circuit()
        self.setup_circuit()

    @staticmethod
    def comp_cb(self, comp):
        self.sig_notify.emit(comp)

    def set_position(self, comp, x, y):
        self._component_position[comp] = QPoint(x, y)

    def get_position(self, comp):
        return self._component_position[comp]

    def setup_circuit(self):
        _bu_a = OnOffSwitch(self._circuit, "SwitchA")
        self.set_position(_bu_a, 20, 20)
        _bu_b = OnOffSwitch(self._circuit, "SwitchB")
        self.set_position(_bu_b, 20, 220)
        _and = AND(self._circuit)
        self.set_position(_and, 200, 100)
        _led = Led(self._circuit, "D")
        self.set_position(_led, 400, 150)
        _bu_a.O.wire = _and.A
        _bu_b.O.wire = _and.B
        _and.Y.wire = _led.I
        _led.set_callback(partial(self.comp_cb, self))
        _bu_a.set_callback(partial(self.comp_cb, self))
        _bu_b.set_callback(partial(self.comp_cb, self))
        self._circuit.init()

    @property
    def circuit(self):
        return self._circuit
