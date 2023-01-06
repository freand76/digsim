import queue
import time
from functools import partial

from PySide6.QtCore import QPoint, QRect, QSize, QThread, Signal

from digsim import (AND, CallbackComponent, Circuit, Clock, Component, Led,
                    OnOffSwitch, PushButton)


class PlacedComponent:

    DEFAULT_WIDTH = 120
    DEFAULT_HEIGHT = 100
    BORDER_MARGIN = 20
    PORT_SIDE = 8
    COMPONENT_BORDER = 5
    PORT_CLICK_EXTRA_PIXELS = 5

    def __init__(self, component, x, y):
        self._component = component
        self._pos = QPoint(x, y)
        self._height = self.DEFAULT_HEIGHT
        self._width = self.DEFAULT_WIDTH
        self._port_rects = {}
        self._add_port_rects(self._component.inports, 0)
        self._add_port_rects(self._component.outports, self._width - self.PORT_SIDE - 1)

    def _add_port_rects(self, ports, x):
        if len(ports) == 1:
            self._port_rects[ports[0].name] = QRect(
                x,
                self._height / 2 - self.PORT_SIDE / 2,
                self.PORT_SIDE,
                self.PORT_SIDE,
            )
        elif len(ports) > 1:
            port_distance = (self._height - 2 * self.BORDER_MARGIN) / (len(ports) - 1)
            for idx, port in enumerate(ports):
                self._port_rects[port.name] = QRect(
                    x,
                    self.BORDER_MARGIN + idx * port_distance - self.PORT_SIDE / 2,
                    self.PORT_SIDE,
                    self.PORT_SIDE,
                )

    def get_rect(self):
        return QRect(
            self.COMPONENT_BORDER,
            self.COMPONENT_BORDER,
            self._width - 2 * self.COMPONENT_BORDER,
            self._height - 2 * self.COMPONENT_BORDER,
        )

    def get_port_pos(self, portname):
        rect = self._port_rects[portname]
        return QPoint(rect.x(), rect.y()) + QPoint(
            self.PORT_SIDE / 2, self.PORT_SIDE / 2
        )

    def get_port_for_point(self, point):
        for portname, rect in self.port_rects.items():
            if (
                point.x() > rect.x() - self.PORT_CLICK_EXTRA_PIXELS
                and point.x() < rect.x() + rect.width() + self.PORT_CLICK_EXTRA_PIXELS
                and point.y() > rect.y() - self.PORT_CLICK_EXTRA_PIXELS
                and point.y() < rect.y() + rect.height() + self.PORT_CLICK_EXTRA_PIXELS
            ):
                return portname
        return None

    @property
    def component(self):
        return self._component

    @property
    def port_rects(self):
        return self._port_rects

    @property
    def pos(self):
        return self._pos

    @property
    def size(self):
        return QSize(self._width, self._height)

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


class AppModel(QThread):

    sig_component_notify = Signal(Component)
    sig_control_notify = Signal(bool)
    sig_sim_time_ms_notify = Signal(float)

    def __init__(self):
        super().__init__()
        self._placed_components = {}
        self._placed_wires = {}
        self._circuit = Circuit(vcd="gui.vcd")
        self._started = False
        self._sim_tick_ms = 50
        self._gui_event_queue = queue.Queue()
        self.setup_circuit()

    @staticmethod
    def comp_cb(self, comp):
        self.sig_component_notify.emit(comp)

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
        _on_off = self.add_component(OnOffSwitch(self._circuit, "Switch"), 20, 20)
        _push_button = self.add_component(
            PushButton(self._circuit, "PushButton"), 20, 220
        )
        _and = self.add_component(AND(self._circuit), 200, 100)
        _led = self.add_component(Led(self._circuit, "Led"), 400, 140)
        _clk = self.add_component(Clock(self._circuit, 1.0, "Clock"), 20, 340)
        _and2 = self.add_component(AND(self._circuit, "AND2"), 200, 300)
        _led2 = self.add_component(Led(self._circuit, "Led2"), 400, 340)
        self.add_wire(_on_off.O, _and.A)
        self.add_wire(_push_button.O, _and.B)
        self.add_wire(_and.Y, _led.I)

        self.add_wire(_push_button.O, _and2.A)
        self.add_wire(_clk.O, _and2.B)
        self.add_wire(_and2.Y, _led2.I)

        self._circuit.init()

    @property
    def circuit(self):
        return self._circuit

    def model_start(self):
        self._started = True
        self.start()
        self.sig_control_notify.emit(self._started)

    def model_stop(self):
        self._started = False

    def model_reset(self):
        if not self._started:
            self._circuit.init()

    def add_gui_event(self, func):
        self._gui_event_queue.put(func)

    def run(self):
        start_time = time.perf_counter()
        next_tick = start_time
        while self._started:
            next_tick += self._sim_tick_ms / 1000

            # Execute one GUI event at a time
            if not self._gui_event_queue.empty():
                gui_event_func = self._gui_event_queue.get()
                gui_event_func()

            self._circuit.run(ms=self._sim_tick_ms)
            now = time.perf_counter()
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.sig_sim_time_ms_notify.emit(self._circuit.time_ns / 1000000)

        self.sig_control_notify.emit(self._started)

    @property
    def is_running(self):
        return self._started
