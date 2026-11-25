# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Run cocotb's tests on a Verilog design: python -m digsim.cocotb --help"""

import sys

from ._launcher import main


sys.exit(main())
