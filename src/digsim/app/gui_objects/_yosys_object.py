# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A yosys component with an image as symbol the GUI """

from PySide6.QtGui import QAction

from ._image_objects import ImageObject


class YosysObject(ImageObject):
    """The class for a Yosys image component placed in the GUI"""

    IMAGE_FILENAME = "images/YOSYS.png"

    def paint_component(self, painter):
        self.paint_component_base(painter)
        self.paint_component_name(painter)

    def add_context_menu_action(self, menu, parent):
        reloadAction = QAction("Reload", menu)
        menu.addAction(reloadAction)
        reloadAction.triggered.connect(self._reload)

    def _reload(self):
        self.component.reload_netlist()
        self._app_model.model_reset()
