from functools import partial

from PySide6.QtCore import QObject, QPoint, Signal

from digsim import AND, CallbackComponent, Circuit, Component, Led, OnOffSwitch


class PlacedComponent:

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    BORDER_MARGIN = 20
    PORT_SIDE = 8

    def __init__(self, component, x, y):
        self._component = component
        self._pos = QPoint(x, y)
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._ports = self.get_port_points(self._component.inports, 0, self._height)
        self._ports.update(
            self.get_port_points(
                self._component.outports, self._width - self.PORT_SIDE - 1, self._height
            )
        )

    @classmethod
    def get_port_points(cls, ports, x, height):
        port_dict = {}
        if len(ports) == 1:
            port_dict[ports[0].name] = QPoint(x, height / 2)
        elif len(ports) > 1:
            port_distance = (height - 2 * cls.BORDER_MARGIN) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                port_dict[port.name] = QPoint(
                    x, cls.BORDER_MARGIN + idx * port_distance
                )
        return port_dict

    def get_port_pos(self, portname):
        return self._ports[portname]

    @property
    def component(self):
        return self._component

    @property
    def ports(self):
        return self._ports

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, point):
        self._pos = point

    def __str__(self):
        return f'{{ "name": "{self.component.name}", "x": {self.pos.x()}, "y": {self.pos.y()} }}'


class PlacedWire:
    def __init__(self, app_model, src_port, dst_port):
        self._app_model = app_model
        self._src_port = src_port
        self._dst_port = dst_port
        self._src_port.wire = self._dst_port
        self._src_point = None
        self._dst_point = None
        self.update()

    def update(self):
        src_comp = self._app_model.get_placed_component(self._src_port.parent)
        dst_comp = self._app_model.get_placed_component(self._dst_port.parent)
        self._src_point = src_comp.pos + src_comp.get_port_pos(self._src_port.name)
        self._dst_point = dst_comp.pos + dst_comp.get_port_pos(self._dst_port.name)

    @property
    def src(self):
        return self._src_point

    @property
    def dst(self):
        return self._dst_point


class AppModel(QObject):

    sig_notify = Signal(Component)

    def __init__(self):
        super().__init__()
        self._placed_components = {}
        self._placed_wires = {}
        self._circuit = Circuit()
        self.setup_circuit()

    @staticmethod
    def comp_cb(self, comp):
        self.sig_notify.emit(comp)

    def get_placed_component(self, component):
        return self._placed_components[component]

    def add_component(self, component, x, y):
        placed_component = PlacedComponent(component, x, y)
        self._placed_components[component] = placed_component
        if isinstance(component, CallbackComponent):
            component.set_callback(partial(self.comp_cb, self))
        return component

    def add_wire(self, src_port, dst_port):
        self._placed_wires[(src_port, dst_port)] = PlacedWire(self, src_port, dst_port)

    def get_placed_components(self):
        placed_components = []
        for _, comp in self._placed_components.items():
            placed_components.append(comp)
        return placed_components

    def get_wires(self):
        wires = []
        for _, wire in self._placed_wires.items():
            wires.append(wire)
        return wires

    def update_wires(self):
        for _, wire in self._placed_wires.items():
            wire.update()

    def setup_circuit(self):
        _bu_a = self.add_component(OnOffSwitch(self._circuit, "SwitchA"), 20, 20)
        _bu_b = self.add_component(OnOffSwitch(self._circuit, "SwitchB"), 20, 220)
        _and = self.add_component(AND(self._circuit), 200, 100)
        _led = self.add_component(Led(self._circuit, "Led"), 400, 140)
        self.add_wire(_bu_a.O, _and.A)
        self.add_wire(_bu_b.O, _and.B)
        self.add_wire(_and.Y, _led.I)
        self._circuit.init()

    @property
    def circuit(self):
        return self._circuit
