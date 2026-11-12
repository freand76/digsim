# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The engine (everything but digsim.app) imports without the GUI and without PySide6, so
that it can be a package of its own
"""

import subprocess
import sys


ENGINE_PACKAGES = ["circuit", "synth", "storage_model", "utils", "verilog"]

# In a new Python: PySide6 and the GUI can't be imported (None in sys.modules makes an
# import of them fail), then every module of the engine is imported
_IMPORT_ALL = f"""
import importlib, pkgutil, sys
sys.modules["PySide6"] = None
sys.modules["digsim.app"] = None
modules = []
for name in {ENGINE_PACKAGES!r}:
    package = importlib.import_module("digsim." + name)
    modules.append(package.__name__)
    for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if not info.name.endswith("__main__"):
            importlib.import_module(info.name)
            modules.append(info.name)
print(len(modules))
"""


def test_engine_imports_without_gui():
    """Every module of the engine imports with PySide6 and digsim.app missing"""
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_ALL], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    # Not an empty walk: the engine has more modules than its packages
    assert int(result.stdout) > 20
