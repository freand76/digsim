# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Generate the screenshot of the Verilog editor (docs/images/verilog_editor.png).

The script adds a Yosys component of a copy of the traffic light example in the real
application, offscreen, opens the editor and synthesizes.

Run from the repository root:

    uv run python docs/scripts/generate_editor_image.py
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


os.environ["QT_QPA_PLATFORM"] = "offscreen"

import platformdirs

from PySide6.QtCore import QEventLoop, QPointF, QTimer
from PySide6.QtWidgets import QApplication

from digsim.app.gui import MainWindow
from digsim.app.model import AppModel


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "images" / "verilog_editor.png"


def spin(ms: int) -> None:
    """Let the application run for 'ms'"""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    # A folder Yosys can read: YoWASP has a private /tmp
    cache_dir = Path(platformdirs.user_cache_dir("digsim", appauthor=False))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_dir, ignore_cleanup_errors=True) as work_dir:
        path = Path(work_dir) / "traffic_light.sv"
        shutil.copy(ROOT / "examples" / "yosys_fsm" / "traffic_light.sv", path)
        model = AppModel()
        window = MainWindow(model, "docs")
        window.show()
        model.objects.components.add_object_by_name(
            "YosysComponent", QPointF(100, 100), {"path": str(path)}
        )
        model.sig_edit_verilog.emit(str(path))
        spin(300)
        (editor,) = window.verilog_editors.editors()
        editor.resize(900, 640)
        editor.code.go_to_line(24)
        editor.synthesize()
        while editor.is_building():
            spin(50)
        spin(300)
        editor.grab().save(str(OUT))
        editor.close()
        model.model_stop()
    print(f"Screenshot written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
