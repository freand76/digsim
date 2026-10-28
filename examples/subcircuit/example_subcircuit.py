# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
Example with a subcircuit: the full adder of the GUI example circuits
(example_circuits/full_adder.circuit), itself made from two half adder subcircuits,
used as a component. Its ports are the In and Out ports of the file: a, b, cin, s and
cout. The example prints its truth table.
"""

import pathlib

from digsim.circuit import Circuit
from digsim.circuit.components import StaticValue, SubCircuit


example_circuits = pathlib.Path(__file__).parent.parent.parent / "example_circuits"

print(" a  b cin |  s cout")
for value in range(8):
    a, b, cin = value >> 2 & 1, value >> 1 & 1, value & 1
    circuit = Circuit()
    adder = SubCircuit(circuit, example_circuits / "full_adder.circuit")
    for port, bit in ((adder.a, a), (adder.b, b), (adder.cin, cin)):
        StaticValue(circuit, value=bit).O.wire = port
    circuit.init()
    circuit.run(ns=100)
    print(f" {a}  {b}  {cin}  |  {adder.s.value}   {adder.cout.value}")
