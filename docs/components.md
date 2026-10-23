# Creating Components

This guide shows how to write your own component for [Python circuits](python.md), step by
step, using two examples:

- **`XNOR`**, a logic gate, high when its inputs are equal.
- **`LedBar`**, a column of LEDs, with one input for each LED.

!!! info
    Both components are part of DigSim, so you can read the finished code:

    - `XNOR` is in
      [`_gates.py`](https://github.com/freand76/digsim/blob/main/src/digsim/circuit/components/_gates.py),
      extended from the two-input version in this guide to 2 to 8 inputs, like the other gates.
    - `LedBar` is in
      [`_led_bar.py`](https://github.com/freand76/digsim/blob/main/src/digsim/circuit/components/_led_bar.py).

Everything here works in your own project, without changing DigSim. To use a component in
the DigSim application too, continue with
[Adding Components to the GUI](gui-components.md).

!!! tip
    If your component can be described in Verilog, you may not need to write a component
    class at all: a [Yosys component](synthesis.md) turns a Verilog module into a component.

## How components work

A component has **ports**, and wires connect an output port of one component to input
ports of other components. A port value is `0`, `1`, a number for buses wider than one
bit, or `"X"` when the value is unknown (for example before the circuit is initialized).

The simulation is event driven. When a component sets an output, an event is scheduled
after the port's delay (1 ns by default). When the event happens, the new value travels
along the wires, and every component with a changed input port gets its `update()` method
called, which may set new outputs, and so on.

### Ports

Ports live in `digsim.circuit.components.atoms`:

| Port | Use |
| --- | --- |
| `PortIn` | An input that calls the component's `update()` when it changes. |
| `PortWire` | An input that does *not* call `update()`, for inputs that are only read when another input changes, such as the `D` input of a flip-flop. |
| `PortOutDelta` | An output that changes after a delay (`delay_ns`, default 1 ns). Use this for logic. |
| `PortOutImmediate` | An output that changes at once, for inputs controlled by the user, such as buttons. |
| `PortMultiBitWire` | A bus port that also gives access to its single bits (`get_bit()`). |

Ports take a `width` argument for buses, for example `PortIn(self, "I", width=8)`. A port
added with `add_port()` becomes an attribute with the port's name, so `self.add_port(PortIn(self, "A"))`
can be used as `self.A` afterwards.

### Base classes

| Base class | Use |
| --- | --- |
| `Component` | Most components. |
| `CallbackComponent` | Components that should notify someone when they change, typically outputs such as LEDs. The callback is called from `update()`, and the GUI uses it to repaint the component. |
| `MultiComponent` | Components built from other components, such as the `SR` latch, built from two `NOR` gates. |

### Methods to implement

| Method | Called |
| --- | --- |
| `__init__()` | Create ports with `add_port()` and store settings with `parameter_set()`. |
| `default_state()` | When the circuit is initialized (`circuit.init()`). Set the initial output values here. |
| `update()` | When a `PortIn` input changes. Compute and set the outputs. |
| `get_parameters()` | A class method describing the settings of the component, see [Parameters](#step-3-add-parameters). |
| `reconfigure()` | After the settings of a placed component have changed in the GUI. |

## Writing a component

### Step 1: Write the component class

An XNOR gate has two inputs and an output that is high when the inputs are equal. Put it in
a module of your own, for example `my_components.py`:

```python
from digsim.circuit.components.atoms import Component, PortIn, PortOutDelta


class XNOR(Component):
    """XNOR logic gate: Y is high when A and B are equal"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == "X" or self.B.value == "X":
            self.Y.value = "X"
        elif self.A.value == self.B.value:
            self.Y.value = 1
        else:
            self.Y.value = 0
```

- `name` is optional. Without it the component is named after its class, and DigSim adds
  `_1`, `_2`, ... when the name is already taken in the circuit.
- Handle `"X"` on the inputs, so that unknown values propagate instead of being treated as
  `0`.

### Step 2: Use it in a circuit

Your component is used like the built-in ones:

```python
from digsim.circuit import Circuit
from digsim.circuit.components import Led, PushButton

from my_components import XNOR


def led_changed(led):
    state = "ON" if led.I.value == 1 else "OFF"
    print(f"{led.circuit.time_ns:>9} ns: {led.name()} is {state}")


circuit = Circuit()
button_a = PushButton(circuit, "A")
button_b = PushButton(circuit, "B")
xnor = XNOR(circuit)
led = Led(circuit, "led", callback=led_changed)

button_a.O.wire = xnor.A
button_b.O.wire = xnor.B
xnor.Y.wire = led.I

circuit.init()
circuit.run(ms=1)  # A=0, B=0: equal, LED on
button_a.push()
circuit.run(ms=1)  # A=1, B=0: different, LED off
button_b.push()
circuit.run(ms=1)  # A=1, B=1: equal, LED on
```

```text
        0 ns: led is OFF
        1 ns: led is ON
  1000001 ns: led is OFF
  2000001 ns: led is ON
```

The LED is off at 0 ns because the XNOR output is still unknown. It turns on 1 ns later,
after the gate delay.

### Step 3: Add parameters

Parameters are settings chosen when a component is created, such as the number of LEDs in
the LED bar. Store each parameter with `parameter_set()` and describe it in
`get_parameters()`:

```python
from digsim.circuit.components.atoms import CallbackComponent, PortIn


class LedBar(CallbackComponent):
    """
    A column of LEDs, with one input for each LED.

    Ports:
        0, 1, ...: Inputs, one for each LED, numbered from 0.

    Args:
        circuit: The circuit to add the component to.
        name: The component name, the class name if not given.
        width: The number of LEDs, 1 to 16.
        color: The color of the LEDs in the GUI: "red", "green", "blue" or "yellow".
    """

    def __init__(self, circuit, name=None, width=8, color="red"):
        super().__init__(circuit, name, callback=None)
        for bit in range(width):
            self.add_port(PortIn(self, f"{bit}"))
        self.parameter_set("width", width)
        self.parameter_set("color", color)

    @property
    def color(self):
        """The color of the LEDs in the GUI"""
        return self.parameter_get("color")

    def lit(self):
        """The state of each LED, LED 0 first"""
        return [port.value == 1 for port in self.inports()]

    @classmethod
    def get_parameters(cls):
        return {
            "width": {
                "type": "int",
                "min": 1,
                "max": 16,
                "default": 8,
                "description": "Number of LEDs",
            },
            "color": {
                "type": "list",
                "items": ["red", "green", "blue", "yellow"],
                "default": "red",
                "description": "Color",
                "reconfigurable": True,
            },
        }
```

!!! important
    Every parameter name must also be an argument of `__init__()`. When a circuit is saved,
    DigSim stores the parameters, and when it is loaded the component is created again with
    them as keyword arguments: `LedBar(circuit=circuit, width=8)`.

`LedBar` is a `CallbackComponent`. It doesn't compute anything, but the callback lets a
user of the component, and the GUI, know when one of its inputs has changed. The inputs
are named `"0"`, `"1"` and so on, which aren't Python names, so they are reached with
`port()`: `led_bar.port("0")`.

The docstring describes the component's ports under `Ports:` and its arguments under
`Args:`. For the components in DigSim, the [API Reference](api/components.md) is generated
from it.

### Step 4: Test it

Components are plain Python, so they are easy to test with [pytest](https://pytest.org/):

```python
from digsim.circuit import Circuit

from my_components import XNOR


def test_xnor():
    circuit = Circuit()
    xnor = XNOR(circuit)
    circuit.init()
    for a, b, y in [(0, 0, 1), (0, 1, 0), (1, 0, 0), (1, 1, 1)]:
        xnor.A.value = a
        xnor.B.value = b
        circuit.run(ns=10)
        assert xnor.Y.value == y
```

Inputs that are not driven by another component can be set directly, as here.

### Saving circuits with your own components

`circuit.to_json_file()` stores each component's type as its module path and class name,
leaving out module names that start with `_`. A component in `my_components.py` is stored
as `my_components.XNOR`, so `my_components` must be importable when the circuit is
loaded again. If it isn't, loading reports the component as an unknown component type.
