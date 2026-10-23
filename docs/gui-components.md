# Adding Components to the GUI

This guide adds the `XNOR` gate and the `LedBar` from [Creating Components](components.md)
to the DigSim application. The XNOR gate gets an image as its symbol, and the LED bar is
drawn by code, so it can show its current value.

![The XNOR and LED bar components in the GUI](images/guide/new_components.png)

The finished code is in DigSim: the GUI objects are in
[`_image_objects.py`](https://github.com/freand76/digsim/blob/main/src/digsim/app/gui_objects/_image_objects.py)
and
[`_led_bar_object.py`](https://github.com/freand76/digsim/blob/main/src/digsim/app/gui_objects/_led_bar_object.py).
Contributions of new components are welcome, see [Contributing](contributing.md).

The GUI can only show components that are part of DigSim, so this changes DigSim's source
code. Start with a [development setup](contributing.md#development-setup). These are
all the steps needed to get a component into the component selector:

1. [Add the component to DigSim](#1-add-the-component-to-digsim)
2. [Export it from `digsim.circuit.components`](#2-export-the-component)
3. Create a GUI object, either [with an image](#3a-a-gui-object-with-an-image) or
   [drawn by code](#3b-a-gui-object-drawn-by-code)
4. [Register the GUI object](#4-register-the-gui-object)
5. [Add the component to the component selector](#5-add-it-to-the-component-selector)
6. [Check the settings dialog](#6-the-settings-dialog)
7. [Try it](#7-try-it)

## 1. Add the component to DigSim

Move the component class to its own module in
[`src/digsim/circuit/components`](https://github.com/freand76/digsim/tree/main/src/digsim/circuit/components),
for example `_xnor.py` and `_led_bar.py`. Module names start with `_`, and the code in
DigSim is type annotated, so the class looks like this:

```python
# src/digsim/circuit/components/_xnor.py
from __future__ import annotations

from typing import TYPE_CHECKING

from .atoms import Component, PortIn, PortOutDelta


if TYPE_CHECKING:
    from digsim.circuit import Circuit


class XNOR(Component):
    """XNOR logic gate: Y is high when A and B are equal"""

    def __init__(self, circuit: Circuit, name: str | None = None) -> None:
        super().__init__(circuit, name)
        ...

    def update(self) -> None: ...
```

## 2. Export the component

Add the class to
[`src/digsim/circuit/components/__init__.py`](https://github.com/freand76/digsim/blob/main/src/digsim/circuit/components/__init__.py):

```python
from ._led_bar import LedBar
from ._xnor import XNOR
```

Both the GUI and saved circuit files find components by their name in
`digsim.circuit.components`. A saved XNOR gate is stored as
`digsim.circuit.components.XNOR`.

## 3a. A GUI object with an image

Each component in the GUI is shown by a *GUI object*, a class in
[`src/digsim/app/gui_objects`](https://github.com/freand76/digsim/tree/main/src/digsim/app/gui_objects).
For a component with a picture as its symbol, subclass `ImageObject` and name the image.
Gates use `GateImageObject`, which also hides the port names. In
[`_image_objects.py`](https://github.com/freand76/digsim/blob/main/src/digsim/app/gui_objects/_image_objects.py):

```python
class ImageObjectXNOR(GateImageObject):
    """The class for a XNOR image component placed in the GUI"""

    IMAGE_FILENAME = "images/XNOR.png"
```

- Put the image in
  [`src/digsim/app/gui_objects/images`](https://github.com/freand76/digsim/tree/main/src/digsim/app/gui_objects/images).
  The existing symbols are PNG files about 70 pixels wide. Files in that folder are
  included in the package (see `MANIFEST.in`).
- Set `ACTIVE_IMAGE_FILENAME` as well to show another image while the component's `active`
  property is `True`, the way the LED lights up.
- Set `SHOW_NAME = False` to leave out the component's name on the image, and
  `SHOW_PORT_NAMES = False` to leave out the port names. `GateImageObject` sets
  `SHOW_PORT_NAMES = False`, and the LED leaves out both.
- The same image is used in the component selector.
- Components with many ports, like ICs and flip-flops, subclass `NamedBoxObject`
  instead. It draws a box with the component's name and port names, and only uses the
  image in the component selector.

## 3b. A GUI object drawn by code

To show the state of a component, draw it in `paint_component()`. Subclass
`ComponentObject`, in a new module such as `_led_bar_object.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QPainter

from digsim.circuit.components import LedBar
from digsim.circuit.components.atoms import Component

from ._component_object import ComponentObject


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class LedBarObject(ComponentObject):
    """The class for a LED bar component placed in the GUI"""

    LED_WIDTH = 8
    LED_HEIGHT = 24
    LED_GAP = 4

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.update_size()

    @property
    def component(self) -> LedBar:
        component = self._component
        assert isinstance(component, LedBar)
        return component

    def update_size(self) -> None:
        leds = len(self.component.lit())
        self.width = 2 * self.inport_x_pos() + 40 + leds * (self.LED_WIDTH + self.LED_GAP)
        self.update_ports()

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)
        # Draw the most significant bit to the left
        xpos = int(self.object_pos.x() + self.inport_x_pos() + 30)
        ypos = int(self.object_pos.y() + self.height / 2 - self.LED_HEIGHT / 2 + 8)
        for led_on in reversed(self.component.lit()):
            self._paint_led(painter, xpos, ypos, led_on)
            xpos += self.LED_WIDTH + self.LED_GAP

    @classmethod
    def _paint_led(cls, painter: QPainter, xpos: int, ypos: int, led_on: bool) -> None:
        painter.setPen(Qt.GlobalColor.black)
        painter.setBrush(Qt.GlobalColor.red if led_on else Qt.GlobalColor.darkRed)
        painter.drawRect(xpos, ypos, cls.LED_WIDTH, cls.LED_HEIGHT)

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        xpos = (size.width() - 6 * (cls.LED_WIDTH + cls.LED_GAP)) // 2
        for led_on in [True, False, True, True, False, False]:
            cls._paint_led(painter, xpos, 20, led_on)
            xpos += cls.LED_WIDTH + cls.LED_GAP
        cls.paint_selectable_component_name(painter, QPoint(0, 0), size, name)
```

| Method | Purpose |
| --- | --- |
| `paint_component(painter)` | Draws the placed component with a `QPainter`. `paint_component_base()` draws the standard rounded box, `paint_component_name()` the name. The box is `self.rect()`, positioned at `self.object_pos`. |
| `paint_selectable_component(painter, size, name)` | A class method that draws the component's icon in the component selector, in a `size` sized area. |
| `update_size()` | Called when the component's settings change. Set `self.width` and `self.height`, then call `update_ports()` to move the ports. |
| `component` | Override it to return the component's own type, so type checkers know its methods. |

`paint_component()` and `paint_selectable_component()` are abstract methods. If a GUI
object class misses one of them, mypy reports it when the class is registered in
[step 4](#4-register-the-gui-object). Python itself doesn't check it while the application
runs, so run mypy (see [Contributing](contributing.md#before-you-submit)).

The GUI repaints a `CallbackComponent` after its `update()` runs, which is why `LedBar`
subclasses it. A plain `Component` is only repainted when something else in the circuit
changes.

!!! note
    Qt drawing functions that take whole pixels, such as `drawRect(x, y, w, h)`, need
    `int` values, so use `int()` around calculated positions.

## 4. Register the GUI object

Map the component's class name to its GUI object in `CLASS_NAME_TO_COMPONENT_OBJECT` in
[`_gui_object_factory.py`](https://github.com/freand76/digsim/blob/main/src/digsim/app/gui_objects/_gui_object_factory.py),
and import the GUI object class there:

```python
CLASS_NAME_TO_COMPONENT_OBJECT: dict[str, type[ComponentObject]] = {
    ...
    "XNOR": ImageObjectXNOR,
    "LedBar": LedBarObject,
}
```

## 5. Add it to the component selector

Add a `SelectableComponentWidget` for the component in `ComponentSelection` in
[`src/digsim/app/gui/_component_selection.py`](https://github.com/freand76/digsim/blob/main/src/digsim/app/gui/_component_selection.py).
The order of the lines is the order in the selector, under the group headings ("Input",
"Output", "Gates", ...). `display_name` sets the label, which is the class name otherwise:

```python
layout.addWidget(SelectableComponentWidget("XNOR", self, circuit_area))
layout.addWidget(SelectableComponentWidget("LedBar", self, circuit_area, display_name="LED bar"))
```

![XNOR in the selector](images/guide/selector_xnor.png){ width="80" }
![LED bar in the selector](images/guide/selector_led_bar.png){ width="80" }

## 6. The settings dialog

When a component is added in the GUI, a settings dialog is created from
`get_parameters()`, with one input per parameter (components without parameters are
placed right away). The parameter's `type` selects the input:

| `type` | Input | Keys |
| --- | --- | --- |
| `int` | Slider | `min`, `max`, `default` |
| `intrange` | Slider over a list of values | `range`, `default_index` |
| `bool` | Checkbox | `default` |
| `str` | Text field | `default`, `single_line` (one line instead of a text box), `invalid_list` (values not allowed) |
| `list` | Drop-down | `items` |
| `width_pow2` | Slider from 0 to 2<sup>width</sup>-1, following a `width` parameter | `default` |
| `width_bool` | One checkbox per bit, following a `width` parameter | `default` |
| `component_name` | Drop-down that selects another component class | `component_list` (class name to description) |
| `ic_name` | Drop-down with the built-in ICs | |
| `path` | File dialog before the other parameters (it must be the first one) | `fileinfo` (file filter), `new_verilog` (asks first to open a file or to make a new Verilog file, which is created with a module). Another parameter with `file_types` (like `[".v", ".sv"]`) is only asked for a file of those types |

Every parameter needs a `description`, the label shown in the dialog. In type-annotated code,
`get_parameters()` returns `dict[str, Parameter]`, with `Parameter` from
`digsim.circuit.components.atoms`, so mypy checks the keys and the `type`. Add
`"reconfigurable": True` to let the user change the parameter later, with **Settings** in
the component's context menu. Afterwards, the component's `reconfigure()`
method and the GUI object's `update_size()` are called.

## Interactive components

Components that the user operates while the simulation runs, like buttons and switches:

- return `True` from the `has_action` property, to get a hand cursor over the component
  while the simulation runs,
- implement `onpress()` and `onrelease()`, called when the component is pressed and
  released with the mouse (or a [keyboard shortcut](gui.md#keyboard-shortcuts-for-inputs))
  while the simulation runs,
- use `PortOutImmediate` outputs,
- return the state from the `active` property, to use `ACTIVE_IMAGE_FILENAME`.

See `PushButton` and `OnOffSwitch` in `src/digsim/circuit/components` for examples. In the
GUI object, `single_click_action()` handles clicks while the simulation is stopped, and
`add_context_menu_action(menu, parent)` adds entries to the context menu.

## 7. Try it

1. Start the application from the source tree: `uv run -m digsim.app`.
2. Add the component from the selector, connect it, and run the simulation.
3. Save the circuit, clear it, and load it again, to check that the parameters are restored.
4. Add a test for the component in `tests/`, and run the checks described in
   [Contributing](contributing.md#before-you-submit).
5. Document the component in the [component reference](gui.md#component-reference), with
   its image in `docs/images/components/`.
