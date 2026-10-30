# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The example circuits of the package, for File > Examples: an example's folder is copied to
a folder of the user's, with the files it uses, and opened from there (kept free from Qt
imports so that it can be tested without a display)
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class Example:
    """An example circuit, a circuit file in the folder of its example"""

    path: Path

    @property
    def folder(self) -> Path:
        """The folder with the circuit and the files it uses"""
        return self.path.parent

    @property
    def title(self) -> str:
        """The name in the menu, the name of the circuit"""
        return self.path.stem


def examples_folder() -> Path:
    """
    The folder of the examples, the package digsim.examples: circuits/ of the repository,
    mapped by setup.py (also for an editable install)
    """
    return Path(str(files("digsim.examples")))


def _subcircuit_paths(path: Path) -> set[Path]:
    """The circuit files that a circuit file has as subcircuits"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        components = data["circuit"]["components"]
    except (OSError, ValueError, KeyError, TypeError):
        return set()
    paths = set()
    for component in components:
        if not isinstance(component, dict) or component.get("type") != (
            "digsim.circuit.components.SubCircuit"
        ):
            continue
        settings = component.get("settings")
        if isinstance(settings, dict) and isinstance(settings.get("path"), str):
            paths.add((path.parent / settings["path"]).resolve())
    return paths


def example_circuits(folder: Path | None = None) -> list[Example]:
    """
    The example circuits, by name. The subcircuits of another circuit of its folder are
    left out: they are copied with it.
    """
    if folder is None:
        folder = examples_folder()
    paths = sorted(folder.glob("*/*.circuit"))
    used: set[Path] = set()
    for path in paths:
        used |= _subcircuit_paths(path)
    examples = [Example(path) for path in paths if path.resolve() not in used]
    return sorted(examples, key=lambda example: example.title.lower())


def copy_example(example: Example, destination: Path) -> Path:
    """
    Copy the folder of an example into a folder, as a new folder with the name of the
    example's folder (and a number after it when that is taken), and return the path of
    the circuit file in it.
    """
    name = example.folder.name
    target = destination / name
    number = 2
    while target.exists():
        target = destination / f"{name}_{number}"
        number += 1
    shutil.copytree(example.folder, target, ignore=shutil.ignore_patterns("__pycache__"))
    return target / example.path.name
