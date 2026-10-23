# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""The open Verilog editors, one for each file"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget

from ._verilog_editor import VerilogEditor


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class VerilogEditors:
    """The editor windows of the main window, by file"""

    def __init__(self, app_model: AppModel, parent: QWidget) -> None:
        self._app_model = app_model
        self._parent = parent
        self._editors: dict[Path, VerilogEditor] = {}

    def open(self, path: str | Path) -> VerilogEditor | None:
        """
        Show the editor of a file, a new one if it isn't open. None if the file can't be
        read (the editor said why).
        """
        key = Path(path).resolve()
        editor = self._editors.get(key)
        if editor is None:
            editor = VerilogEditor(self._app_model, key, self._parent)
            if not editor.loaded:
                editor.deleteLater()
                return None
            self._editors[key] = editor
            editor.destroyed.connect(lambda: self._editors.pop(key, None))
        editor.show()
        editor.raise_()
        editor.activateWindow()
        return editor

    def components_updated(self, path: str) -> None:
        """The components of a file were updated from it"""
        editor = self._editors.get(Path(path).resolve())
        if editor is not None:
            editor.components_updated()

    def editors(self) -> list[VerilogEditor]:
        """The open editors"""
        return list(self._editors.values())

    def close_all(self) -> bool:
        """Close the editors, asking to save changes. False if that was cancelled."""
        for editor in self.editors():
            if not editor.close_for_app():
                return False
            # Closed: WA_DeleteOnClose deletes it later
            self._editors.pop(editor.path, None)
        return True
