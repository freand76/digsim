# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
A component built from a Verilog file
"""

from ._yosys_component import YosysComponent


class VerilogComponent(YosysComponent):
    """
    A component built from a Verilog file (or a Yosys JSON netlist), named after its
    module. It is a YosysComponent, by a name that says what it is made from: Yosys
    synthesizes the Verilog into the netlist that DigSim simulates. It takes the same
    arguments.

    Ports:
        The ports of the Verilog module, with the same names and widths. An inout port is
            a PortInOut, wire it both ways to another inout port.

    Example:
        ```python
        counter = VerilogComponent(circuit, "counter.v", functional=True)
        ```
    """
