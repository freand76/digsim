# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A yosys component with an image as symbol the GUI"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QGraphicsSceneMouseEvent, QMenu, QWidget

from digsim.app._yosys_interface import load_netlists
from digsim.app.editor import update_yosys_components
from digsim.circuit.components import YosysComponent
from digsim.circuit.components.atoms import DigsimException

from ._named_box_object import NamedBoxObject


class YosysObject(NamedBoxObject):
    """The class for a Yosys image component placed in the GUI"""

    ICON_TEXT = "Verilog"

    @property
    def component(self) -> YosysComponent:
        component = self._component
        assert isinstance(component, YosysComponent)
        return component

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """QT event callback function: view the netlist, also while it runs"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._app_model.sig_view_subcircuit.emit(self.component.name())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        path = self.component.source_file
        if path is not None and path.endswith((".v", ".sv")):
            editAction = QAction("Edit Verilog...", menu)
            menu.addAction(editAction)
            editAction.triggered.connect(lambda: self._app_model.sig_edit_verilog.emit(path))
        view_action = QAction("View Netlist", menu)
        menu.addAction(view_action)
        view_action.triggered.connect(
            lambda: self._app_model.sig_view_subcircuit.emit(self.component.name())
        )
        reloadAction = QAction("Reload", menu)
        menu.addAction(reloadAction)
        reloadAction.triggered.connect(lambda: self._reload(parent))

    def _reload(self, parent: QWidget | None) -> None:
        path = self.component.source_file
        if path is None:
            return
        components = self._app_model.objects.components.yosys_components(path)
        try:
            # Yosys always runs: an `include file or a $readmemh file may have changed,
            # which the cached netlists don't know
            variants = {component.variant for component in components}
            netlists = load_netlists(path, variants, cached=False)
            update = self._app_model.objects.components.prepare_yosys_update(path, netlists)
            update_yosys_components(parent, self._app_model, update)
        except (DigsimException, OSError) as exc:
            # OSError: the file has been moved or can't be read
            self._app_model.sig_warning_log.emit("Reload Yosys Warning", str(exc))
