# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A yosys component with an image as symbol the GUI"""

from PySide6.QtGui import QAction, QPainter
from PySide6.QtWidgets import QMenu, QWidget

from digsim.circuit.components import YosysComponent
from digsim.circuit.components.atoms import DigsimException

from ._image_objects import ImageObject


class YosysObject(ImageObject):
    """The class for a Yosys image component placed in the GUI"""

    IMAGE_FILENAME = "images/YOSYS.png"

    @property
    def component(self) -> YosysComponent:
        component = self._component
        assert isinstance(component, YosysComponent)
        return component

    def paint_component(self, painter: QPainter) -> None:
        self.paint_component_base(painter)
        self.paint_component_name(painter)

    def add_context_menu_action(self, menu: QMenu, parent: QWidget | None) -> None:
        reloadAction = QAction("Reload", menu)
        menu.addAction(reloadAction)
        reloadAction.triggered.connect(self._reload)

    def _reload(self) -> None:
        try:
            self.component.reload_file()
        except (DigsimException, OSError) as exc:
            # OSError: the file has been moved or can't be read
            self._app_model.sig_warning_log.emit("Reload Yosys Warning", str(exc))
        self._app_model.model_reset()
