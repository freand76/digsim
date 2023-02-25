# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A selectable object placed in the GUI """

import abc


class GuiObject(abc.ABC):
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

    @classmethod
    def point_in_rect(cls, point, rect):
        """Helper function to test if point is within rectangle"""
        # Make rect positive
        if rect.width() < 0:
            rect.setWidth(-rect.width())
            rect.translate(-rect.width(), 0)
        if rect.height() < 0:
            rect.setHeight(-rect.height())
            rect.translate(0, -rect.height())
        rx2, ry2 = rect.x() + rect.width(), rect.y() + rect.height()
        if rect.x() < point.x() and point.x() < rx2:
            if rect.y() < point.y() and point.y() < ry2:
                return True
        return False

    @abc.abstractmethod
    def in_rect(self, rect):
        """Return True is whole object is within rect"""
