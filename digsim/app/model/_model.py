import queue
import time
from functools import partial

from digsim import (
    AND,
    CallbackComponent,
    Circuit,
    Clock,
    Component,
    HexDigit,
    JsonComponent,
    Led,
    OnOffSwitch,
    PushButton,
)
from PySide6.QtCore import QThread, Signal

from ._placed_component import PlacedComponent
from ._placed_hexdigit import PlacedHexDigit
from ._placed_wire import PlacedWire


class AppModel(QThread):

    sig_component_notify = Signal(Component)
    sig_control_notify = Signal(bool)
    sig_sim_time_notify = Signal(float)

    def __init__(self):
        super().__init__()
        self._placed_components = {}
        self._placed_wires = {}
        self._circuit = Circuit(vcd="gui.vcd")
        self._started = False
        self._sim_tick_ms = 50
        self._gui_event_queue = queue.Queue()
        self._component_callback_list = []
        self.setup_circuit()
        self._new_wire = None
        self._new_wire_end_pos = None

    @staticmethod
    def comp_cb(self, comp):
        if comp not in self._component_callback_list:
            self._component_callback_list.append(comp)

    def get_placed_component(self, component):
        return self._placed_components[component]

    def add_component(self, component, x, y):
        if isinstance(component, HexDigit):
            placed_component = PlacedHexDigit(component, x, y)
        else:
            placed_component = PlacedComponent(component, x, y)

        self._placed_components[component] = placed_component
        if isinstance(component, CallbackComponent):
            component.set_callback(partial(self.comp_cb, self))
        return component

    def add_wire(self, src_port, dst_port):
        wire = PlacedWire(self, src_port, dst_port)
        self._placed_wires[wire.key] = wire

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

    def paint_wires(self, painter):
        wires = self.get_wires()
        for wire in wires:
            wire.paint(painter)

        if self._new_wire is not None and self._new_wire_end_pos is not None:
            self._new_wire.paint_new(painter, self._new_wire_end_pos)

    def new_wire_start(self, component, portname):
        self._new_wire = PlacedWire(self, component.port(portname))

    def new_wire_end(self, component, portname):
        try:
            self._new_wire.set_end_port(component.port(portname))
            self._new_wire.connect()
            self._placed_wires[self._new_wire.key] = self._new_wire
        except Exception as e:
            print("ERROR:", str(e))

        self._new_wire = None
        self._new_wire_end_pos = None

    def set_new_wire_end_pos(self, pos):
        self._new_wire_end_pos = pos

    def has_new_wire(self):
        return self._new_wire is not None

    def setup_circuit(self):
        _on_off = self.add_component(OnOffSwitch(self._circuit, "Switch"), 20, 20)
        _push_button = self.add_component(PushButton(self._circuit, "PushButton"), 20, 220)
        _and = self.add_component(AND(self._circuit), 200, 100)
        _led = self.add_component(Led(self._circuit, "Led"), 400, 140)
        _clk = self.add_component(Clock(self._circuit, 5.0, "Clock"), 20, 340)
        _and2 = self.add_component(AND(self._circuit, "AND2"), 200, 300)
        _led2 = self.add_component(Led(self._circuit, "Led2"), 400, 340)

        _counter = self.add_component(
            JsonComponent(self._circuit, "json_modules/counter.json"), 600, 300
        )
        _hex = self.add_component(HexDigit(self._circuit, "HexDigit", dot=True), 800, 100)
        self._hex = _hex
        self.add_wire(_on_off.O, _and.A)
        self.add_wire(_push_button.O, _and.B)
        self.add_wire(_and.Y, _led.I)

        self.add_wire(_push_button.O, _and2.A)
        self.add_wire(_clk.O, _and2.B)
        self.add_wire(_and2.Y, _led2.I)

        self.add_wire(_clk.O, _counter.clk)
        self.add_wire(_on_off.O, _counter.up)
        self.add_wire(_push_button.O, _counter.reset)
        self.add_wire(_counter.cnt, _hex.val)
        self.add_wire(_clk.O, _hex.dot)
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
            for _, comp in self._placed_components.items():
                self.sig_component_notify.emit(comp.component)

    def add_gui_event(self, func):
        self._gui_event_queue.put(func)

    def run(self):
        start_time = time.perf_counter()
        next_tick = start_time
        while self._started:
            next_tick += self._sim_tick_ms / 1000

            self._component_callback_list = []

            # Execute one GUI event at a time
            if not self._gui_event_queue.empty():
                gui_event_func = self._gui_event_queue.get()
                gui_event_func()

            self._circuit.run(ms=self._sim_tick_ms)

            for comp in self._component_callback_list:
                self.sig_component_notify.emit(comp)

            now = time.perf_counter()
            sleep_time = next_tick - now
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.sig_sim_time_notify.emit(self._circuit.time_ns / 1000000000)

        self.sig_control_notify.emit(self._started)

    @property
    def is_running(self):
        return self._started
