# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A selectable object placed in the GUI """


class PlacedObject:
    """The base class for a selectable object placed in the GUI"""

    def __init__(self):
        self._selected = False

    def select(self, selected=True):
        """Set the selected variable for the current object"""
        self._selected = selected

    @property
    def selected(self):
        """Get the selected variable for the current object"""
        return self._selected
