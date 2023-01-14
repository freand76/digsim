# Copyright (c) Fredrik Andersson, 2023
# All rights reserved


class PlacedObject:
    def __init__(self):
        self._selected = False

    def select(self, selected=True):
        self._selected = selected

    @property
    def selected(self):
        return self._selected
