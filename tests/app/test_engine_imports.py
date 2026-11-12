# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The GUI only uses the public names of the engine (digsim-engine, a package of its own):
a private module or name (with a leading _) can change in the engine without notice
"""

import ast
from pathlib import Path


APP = Path(__file__).parent.parent.parent / "src" / "digsim" / "app"


def _private(dotted: str) -> bool:
    """A dotted name with a private part, like digsim.circuit.components._memory"""
    return any(part.startswith("_") and not part.startswith("__") for part in dotted.split("."))


def private_imports(source: str) -> list[str]:
    """The imports of private engine modules and names in Python source"""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level or not module.startswith("digsim.") or module.startswith("digsim.app"):
                continue
            if _private(module):
                found.append(f"line {node.lineno}: from {module} import ...")
            found.extend(
                f"line {node.lineno}: from {module} import {alias.name}"
                for alias in node.names
                if _private(alias.name)
            )
        elif isinstance(node, ast.Import):
            found.extend(
                f"line {node.lineno}: import {alias.name}"
                for alias in node.names
                if alias.name.startswith("digsim.")
                and not alias.name.startswith("digsim.app")
                and _private(alias.name)
            )
    return found


def test_app_uses_public_engine_names():
    """No module of digsim.app imports a private module or name of the engine"""
    found = {
        str(path.relative_to(APP)): imports
        for path in sorted(APP.rglob("*.py"))
        if (imports := private_imports(path.read_text(encoding="utf-8")))
    }
    assert found == {}


def test_private_imports_found():
    """The check finds private engine imports, and leaves the app's own and public ones"""
    source = """
from digsim.circuit.components._memory import read_memory_file
from digsim.circuit.components import _FILEINFO, RAM
import digsim.circuit.components._splitter
from digsim.app.gui._hex_editor import HexEditorDialog
from digsim.circuit.components import RAM, ROM
from ._wire_path import WirePath
"""
    assert private_imports(source) == [
        "line 2: from digsim.circuit.components._memory import ...",
        "line 3: from digsim.circuit.components import _FILEINFO",
        "line 4: import digsim.circuit.components._splitter",
    ]
