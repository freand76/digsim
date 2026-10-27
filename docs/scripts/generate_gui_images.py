# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Generate the images of the GUI documentation that are not tutorial steps: the component
images of the GUI reference (docs/images/components/ and the digits and the note), the
screenshots of the application and the main window, and the images of the guide to
adding components (docs/images/guide/). Also draws the application icon
(src/digsim/app/images/app_icon.png, and its copy docs/images/app_icon.png).

Each component is drawn by its GUI object, the way the application draws it, after a
short simulation that lights its LEDs or sets its switches.

Run from the repository root:

    uv run python docs/scripts/generate_gui_images.py
"""

from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import chdir
from pathlib import Path
from typing import Any


os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsScene, QScrollArea

from digsim.app.gui import MainWindow
from digsim.app.gui._circuit_area import CircuitArea
from digsim.app.gui._component_selection import SelectableComponentWidget
from digsim.app.gui._top_bar import TopBar
from digsim.app.gui_objects import _theme as theme
from digsim.app.gui_objects import class_factory
from digsim.app.model import AppModel
from digsim.circuit import Circuit, components
from digsim.circuit.components.atoms import Component


ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "docs" / "images"
# The component images are drawn larger than in the application, like the old images
SCALE = 1.5
WINDOW_SIZE = (1380, 740)


def spin(ms: int) -> None:
    """Let the application run (events and repaints) for 'ms'"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def driven(value: int, port: str = "I") -> Callable[[Circuit, Component], None]:
    """A setup that drives an input of the component with a static value"""

    def setup(circuit: Circuit, component: Component) -> None:
        width = component.port(port).width
        static = components.StaticValue(circuit, width=width, value=value)
        static.O.wire = component.port(port)

    return setup


def lit_ports(names: list[str]) -> Callable[[Circuit, Component], None]:
    """A setup that drives some one-bit inputs of the component with 1"""

    def setup(circuit: Circuit, component: Component) -> None:
        for name in names:
            static = components.StaticValue(circuit, value=1)
            static.O.wire = component.port(name)

    return setup


def clocked(names: list[str]) -> Callable[[Circuit, Component], None]:
    """A setup that connects clocks to inputs of the component"""

    def setup(circuit: Circuit, component: Component) -> None:
        for frequency, name in enumerate(names, start=2):
            clock = components.Clock(circuit, frequency=frequency)
            clock.O.wire = component.port(name)

    return setup


def after_init(action: Callable[[Component], None]) -> Callable[[Circuit, Component], None]:
    """A setup that operates the component when the circuit has started"""

    def setup(circuit: Circuit, component: Component) -> None:
        circuit.init()
        action(component)

    setup.inits = True  # type: ignore[attr-defined]
    return setup


def dip_switch(component: Component) -> None:
    assert isinstance(component, components.DipSwitch)
    for bit in (0, 2):
        component.select(bit)
        component.toggle()
    component.select(None)


# (file, component class, settings, setup)
COMPONENT_IMAGES: list[tuple[str, str, dict[str, Any], Callable[..., None] | None]] = [
    ("components/PB.png", "PushButton", {}, after_init(lambda c: c.push())),
    ("components/Switch_ON.png", "OnOffSwitch", {}, after_init(lambda c: c.turn_on())),
    ("components/DIP_SWITCH.png", "DipSwitch", {"bits": 4}, after_init(dip_switch)),
    ("components/Clock.png", "Clock", {}, None),
    ("components/ZERO.png", "StaticValue", {}, None),
    ("components/LED_ON.png", "Led", {}, driven(1)),
    ("components/LedBar.png", "LedBar", {"width": 8}, lit_ports(["1", "2", "4", "7"])),
    ("HexDigit.png", "HexDigit", {}, driven(10, "val")),
    ("SevenSegment.png", "SevenSegment", {}, lit_ports(["A", "B", "G", "E", "D"])),
    ("components/Buzzer.png", "Buzzer", {}, driven(1)),
    ("components/Analyzer.png", "LogicAnalyzer", {}, clocked(["A", "B", "C"])),
    ("components/Probe.png", "Probe", {"width": 8}, driven(0x2A)),
    ("components/OR.png", "OR", {}, None),
    ("components/AND.png", "AND", {}, None),
    ("components/NOT.png", "NOT", {}, None),
    ("components/XOR.png", "XOR", {}, None),
    ("components/XNOR.png", "XNOR", {}, None),
    ("components/NAND.png", "NAND", {}, None),
    ("components/NOR.png", "NOR", {}, None),
    ("components/DFF.png", "DFF", {}, None),
    ("components/FlipFlop.png", "ClockedJKFF", {}, None),
    ("components/MUX.png", "MUX", {}, None),
    ("components/TRISTATE.png", "TristateBuffer", {}, None),
    ("components/RAM.png", "RAM", {}, None),
    (
        "components/ROM.png",
        "ROM",
        {
            "path": str(ROOT / "examples" / "yosys_6502" / "code.bin"),
            "address_width": 11,
            "output_enable": True,
        },
        None,
    ),
    ("components/IC.png", "IntegratedCircuit", {"ic_name": "7485"}, None),
    (
        "components/YOSYS.png",
        "YosysComponent",
        {"path": str(ROOT / "examples" / "yosys_counter" / "counter.v")},
        None,
    ),
    ("Note.png", "Note", {"text": "A note about the circuit"}, None),
]


def render_component(model: AppModel, name: str, settings: dict[str, Any], setup: Any) -> QImage:
    """A component as the application draws it, on a transparent background"""
    circuit = Circuit()
    component = getattr(components, name)(circuit, **settings)
    if setup is not None:
        setup(circuit, component)
    if not getattr(setup, "inits", False):
        circuit.init()
    circuit.run(ms=1500)
    component_object = class_factory(name)(model, component, 0, 0)
    scene = QGraphicsScene()
    scene.addItem(component_object)
    source = component_object.mapRectToScene(
        component_object.boundingRect().united(component_object.childrenBoundingRect())
    ).adjusted(-2, -2, 2, 2)
    image = QImage(
        int(source.width() * SCALE), int(source.height() * SCALE), QImage.Format.Format_ARGB32
    )
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    scene.render(painter, QRectF(image.rect()), source)
    painter.end()
    return image


def component_images(model: AppModel) -> None:
    for file, name, settings, setup in COMPONENT_IMAGES:
        render_component(model, name, settings, setup).save(str(IMAGES / file))


def selector_icon(window: MainWindow, name: str, display_name: str) -> QImage:
    """The icon of a component in the component selector"""
    area = window.findChild(CircuitArea)
    assert area is not None
    widget = SelectableComponentWidget(name, window, area, display_name=display_name)
    widget.resize(80, 105)
    return widget.grab().toImage()


def window_screenshots(model: AppModel, window: MainWindow) -> None:
    area = window.findChild(CircuitArea)
    assert area is not None

    # The application with the Verilog counter
    with chdir(ROOT):
        model.load_circuit("example_circuits/counter_yosys_netlist.circuit")
    # Running, with the switch on: the counter counts and the analyzer shows it
    model.model_start()
    spin(300)
    for component in model.objects.circuit.get_toplevel_components():
        if isinstance(component, components.OnOffSwitch):
            component.turn_on()
    spin(3000)
    area.centerOn(QPointF(700, 300))
    spin(200)
    window.grab().save(str(IMAGES / "screenshot_digsim_app.png"))
    model.model_stop()
    spin(300)

    # The main window and its three areas
    model.clear_circuit()
    spin(100)
    add = model.objects.components.add_object_by_name
    button = add("PushButton", QPointF(260, 200), {})
    led = add("Led", QPointF(560, 290), {})
    assert button is not None and led is not None
    model.objects.wires.connect_ports(button.component.O, led.component.I)
    model.sig_synchronize_gui.emit()
    area.centerOn(QPointF(500, 260))
    spin(300)
    pixmap = window.grab()
    painter = QPainter(pixmap)
    # The component selection and the search above it
    selection = area.parentWidget().findChild(QScrollArea)
    assert selection is not None
    for widget, color in (
        (window.findChild(TopBar), QColor(0, 200, 0)),
        (selection.parentWidget(), QColor(0, 0, 255)),
        (area, QColor(255, 0, 0)),
    ):
        assert widget is not None
        rect = QRect(widget.mapTo(window, QPoint(0, 0)), widget.size()).adjusted(2, 2, -2, -2)
        painter.setPen(QPen(color, 4))
        painter.drawRect(rect)
    painter.end()
    pixmap.save(str(IMAGES / "CircuitEditor.png"))
    model.clear_circuit()


def guide_images(model: AppModel, window: MainWindow) -> None:
    """The XNOR gate and the LED bar of the guide to adding components"""
    selector_icon(window, "XNOR", "XNOR").save(str(IMAGES / "guide" / "selector_xnor.png"))
    selector_icon(window, "LedBar", "LED bar").save(str(IMAGES / "guide" / "selector_led_bar.png"))
    area = window.findChild(CircuitArea)
    assert area is not None
    add = model.objects.components.add_object_by_name
    objects = {
        "button": add("PushButton", QPointF(20, 20), {}),
        "switch": add("OnOffSwitch", QPointF(20, 100), {}),
        "xnor": add("XNOR", QPointF(160, 50), {}),
        # Its input at the height of the output of the XNOR
        "led": add("Led", QPointF(300, 40), {"color": "green"}),
        "dip": add("DipSwitch", QPointF(20, 200), {"bits": 4}),
        "bar": add("LedBar", QPointF(160, 200), {"width": 4}),
    }
    parts = {name: obj.component for name, obj in objects.items() if obj is not None}
    wires = model.objects.wires
    wires.connect_ports(parts["button"].O, parts["xnor"].A)
    wires.connect_ports(parts["switch"].O, parts["xnor"].B)
    wires.connect_ports(parts["xnor"].Y, parts["led"].I)
    for bit in range(4):
        wires.connect_ports(parts["dip"].port(f"{bit}"), parts["bar"].port(f"{bit}"))
    model.sig_synchronize_gui.emit()
    model.model_init()
    dip = parts["dip"]
    assert isinstance(dip, components.DipSwitch)
    dip_switch(dip)
    model.objects.circuit.run(ms=100)
    model.objects.components.update_callback_objects()
    spin(300)
    rect = QRectF()
    for component_object in model.objects.get_list():
        component_object.setSelected(False)
        rect = rect.united(component_object.sceneBoundingRect())
    rect = rect.adjusted(-15, -15, 15, 15)
    image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    painter.translate(-rect.left(), -rect.top())
    area.drawBackground(painter, rect)
    painter.resetTransform()
    area.scene().render(painter, QRectF(image.rect()), rect)
    painter.end()
    image.save(str(IMAGES / "guide" / "new_components.png"))
    model.clear_circuit()


def app_icon() -> None:
    """A white square wave on a rounded square in the accent color"""
    size = 256
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.ACCENT)
    painter.drawRoundedRect(QRectF(8, 8, size - 16, size - 16), 48, 48)
    wave = QPainterPath(QPointF(40, 168))
    for x in (40, 128):
        wave.lineTo(x + 26, 168)
        wave.lineTo(x + 26, 88)
        wave.lineTo(x + 70, 88)
        wave.lineTo(x + 70, 168)
    wave.lineTo(216, 168)
    pen = QPen(QColor("#ffffff"), 14)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(wave)
    painter.end()
    for path in (ROOT / "src" / "digsim" / "app" / "images", IMAGES):
        image.save(str(path / "app_icon.png"))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None  # keep the application alive while drawing
    model = AppModel()
    window = MainWindow(model, "docs")
    window.resize(*WINDOW_SIZE)
    window.show()
    spin(300)
    app_icon()
    component_images(model)
    window_screenshots(model, window)
    guide_images(model, window)
    # Not "are you sure" about the circuit when the window closes
    model._changed = False
    print(f"Images written to {IMAGES.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
