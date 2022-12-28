from functools import partial

from PyQt5.QtCore import QObject, pyqtSignal

from digsim import AND, Circuit, Component, Led, OnOffSwitch


class AppModel(QObject):

    sig_notify = pyqtSignal(Component)

    def __init__(self):
        super().__init__()
        self._circuit = Circuit()
        self.setup_circuit()

    @staticmethod
    def comp_cb(self, comp):
        self.sig_notify.emit(comp)

    def setup_circuit(self):
        _bu_a = OnOffSwitch(self._circuit, "SwitchA")
        _bu_b = OnOffSwitch(self._circuit, "SwitchB")
        _and = AND(self._circuit)
        _led = Led(self._circuit, "D")
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
