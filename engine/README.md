# digsim-engine

The simulator of [DigSim](https://github.com/freand76/digsim), without its GUI: digital
logic circuits in Python, Verilog synthesized by Yosys (which runs in-process, nothing
else to install), VCD files for GTKWave, and the circuit files of the GUI.

```sh
pip install digsim-engine
```

```python
from digsim.circuit import Circuit
from digsim.circuit.components import AND, PushButton

circuit = Circuit(vcd="and.vcd")
a = PushButton(circuit, "a")
b = PushButton(circuit, "b")
gate = AND(circuit, "gate")
a.O.wire = gate.A
b.O.wire = gate.B
circuit.init()
a.push()
b.push()
circuit.run(ns=10)
print(gate.Y.value)  # 1
```

The GUI application, `pip install digsim-logic-simulator`, uses this package. See the
[documentation](https://freand76.github.io/digsim/) for the Python API, Verilog components
and testbenches with pytest.
