# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""The main class module of the digsim.app namespace"""

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())
