# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
DigSim as a cocotb simulator (a proof of concept): `python -m digsim.cocotb` synthesizes a
Verilog design with Yosys and runs cocotb's tests on it, in one process
"""

from ._launcher import main


__all__ = ["main"]
