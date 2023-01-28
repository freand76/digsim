# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A yosys component placed in the GUI """

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from ._placed_component import PlacedComponent


class PlacedYosys(PlacedComponent):
    """The class for a 7-segment component placed in the GUI"""

    def create_context_menu(self, parent, event):
        menu = QMenu(parent)
        action = QAction("Settings")
        action.triggered.connect(self.open_settings)
        menu.addAction(action)
        menu.exec_(event.globalPos())

    def open_settings(self):
        """Open settings dialog"""
        self.component.load("yosys_modules/counter.json")
        self.update_ports()
