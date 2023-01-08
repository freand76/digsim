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
    PortDirection,
    PushButton,
)
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QThread, Signal
from PySide6.QtGui import QFont, QPainterPath, QPen


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

    def paint_component_base(self, painter):
        # Draw component
        comp_rect = self.get_rect()
        painter.setPen(Qt.black)
        painter.setBrush(Qt.SolidPattern)
        if self.component.active:
            painter.setBrush(Qt.green)
        else:
            painter.setBrush(Qt.gray)
        painter.drawRoundedRect(comp_rect, 5, 5)

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(self.get_rect(), Qt.AlignCenter, self._component.name)

    def paint_ports(self, painter, active_port):
        # Draw ports
        painter.setPen(Qt.black)
        painter.setBrush(Qt.SolidPattern)
        painter.setFont(QFont("Arial", 8))
        for portname, rect in self.port_rects.items():
            if portname == active_port:
                painter.setBrush(Qt.red)
            else:
                painter.setBrush(Qt.gray)
            painter.drawRect(rect)

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
        return QPoint(rect.x(), rect.y()) + QPoint(self.PORT_SIDE / 2, self.PORT_SIDE / 2)

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


class PlacedHexDigit(PlacedComponent):

    SEGMENT_TYPE_AND_POS = {
        "A": ("H", QPoint(51, 20)),
        "B": ("V", QPoint(79, 23)),
        "C": ("V", QPoint(79, 53)),
        "D": ("H", QPoint(51, 81)),
        "E": ("V", QPoint(48, 53)),
        "F": ("V", QPoint(48, 23)),
        "G": ("H", QPoint(51, 51)),
    }

    SEGMENT_CORDS = {
        "V": [
            QPoint(3, 3),
            QPoint(3, 20),
            QPoint(0, 25),
            QPoint(-3, 20),
            QPoint(-3, 3),
            QPoint(0, 0),
        ],
        "H": [
            QPoint(3, 3),
            QPoint(20, 3),
            QPoint(25, 0),
            QPoint(20, -3),
            QPoint(3, -3),
            QPoint(0, 0),
        ],
    }

    def paint_component(self, painter):
        self.paint_component_base(painter)
        painter.setBrush(Qt.SolidPattern)
        painter.setPen(Qt.black)
        painter.setBrush(Qt.black)
        painter.drawRoundedRect(33, 10, 60, 80, 3, 3)

        active_segments = self.component.segments()
        for seg, type_pos in self.SEGMENT_TYPE_AND_POS.items():
            if seg in active_segments:
                painter.setPen(Qt.red)
                painter.setBrush(Qt.red)
            else:
                painter.setPen(Qt.darkRed)
                painter.setBrush(Qt.darkRed)
            pos_vector = self.SEGMENT_CORDS[type_pos[0]]
            offset = type_pos[1]
            path = QPainterPath()
            path.moveTo(offset)
            for point in pos_vector:
                path.lineTo(offset + point)
            path.closeSubpath()
            painter.drawPath(path)

        if "." in active_segments:
            painter.setPen(Qt.red)
            painter.setBrush(Qt.red)
        else:
            painter.setPen(Qt.darkRed)
            painter.setBrush(Qt.darkRed)
        painter.drawEllipse(80, 80, 5, 5)


class PlacedWire:
    def __init__(self, app_model, port_a, port_b=None):
        self._app_model = app_model
        self._src_port = None
        self._dst_port = None
        self._connected = False

        if port_a is None:
            raise Exception("Cannot start a wire without a port")

        if port_b is not None:
            if port_a.direction == PortDirection.OUT and port_b.direction == PortDirection.IN:
                self._src_port = port_a
                self._dst_port = port_b
            elif port_a.direction == PortDirection.IN and port_b.direction == PortDirection.OUT:
                self._src_port = port_b
                self._dst_port = port_a
            else:
                raise Exception("Cannot connect to power of same type")
        else:
            if port_a.direction == PortDirection.OUT:
                self._src_port = port_a
            else:
                self._dst_port = port_a

        self._src_point = None
        self._dst_point = None
        self.update()
        self.connect()

    def connect(self):
        if self._src_port is not None and self._dst_port is not None:
            self._src_port.wire = self._dst_port
            self._connected = True

    def set_end_port(self, port):
        if port.direction == PortDirection.OUT and self._src_port is None:
            self._src_port = port
        elif port.direction == PortDirection.IN and self._dst_port is None:
            self._dst_port = port
        else:
            raise Exception("Cannot connect to power of same type")

        self.update()

    def update(self):
        if self._src_port is not None:
            src_comp = self._app_model.get_placed_component(self._src_port.parent)
            self._src_point = src_comp.pos + src_comp.get_port_pos(self._src_port.name)
        if self._dst_port is not None:
            dst_comp = self._app_model.get_placed_component(self._dst_port.parent)
            self._dst_point = dst_comp.pos + dst_comp.get_port_pos(self._dst_port.name)

    @property
    def src_port(self):
        return self._src_port

    @property
    def dst_port(self):
        return self._dst_port

    @property
    def src(self):
        return self._src_point

    @property
    def dst(self):
        return self._dst_point

    @property
    def start_pos(self):
        if self._src_point is not None:
            return self._src_point
        return self._dst_point


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

    def paint_wires(self, painter):
        pen = QPen()
        pen.setWidth(2)
        pen.setColor(Qt.darkGray)
        painter.setPen(pen)
        wires = self.get_wires()
        for wire in wires:
            painter.drawLine(wire.src, wire.dst)

        if self._new_wire is not None and self._new_wire_end_pos is not None:
            painter.drawLine(self._new_wire.start_pos, self._new_wire_end_pos)

    def new_wire_start(self, component, portname):
        self._new_wire = PlacedWire(self, component.port(portname))

    def new_wire_end(self, component, portname):
        try:
            self._new_wire.set_end_port(component.port(portname))
            self._new_wire.connect()
            self._placed_wires[(self._new_wire.src_port, self._new_wire.dst_port)] = self._new_wire
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
        self.add_wire(_counter.cnt0, _hex.I0)
        self.add_wire(_counter.cnt1, _hex.I1)
        self.add_wire(_counter.cnt2, _hex.I2)
        self.add_wire(_counter.cnt3, _hex.I3)
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
