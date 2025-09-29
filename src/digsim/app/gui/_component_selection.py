# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module for the component selection classes"""

from functools import partial

from PySide6.QtCore import QMimeData, QSize, Qt, QTimer
from PySide6.QtGui import QDrag, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

import digsim.app.gui_objects


class SelectableComponentWidget(QPushButton):
    """
    The selectable component class,
    this is the component widget than can be dragged into the circuit area.
    """

    def __init__(self, name, parent, circuit_area, display_name=None):
        super().__init__(parent)
        self._name = name
        self._circuit_area = circuit_area
        self._paint_class = digsim.app.gui_objects.class_factory(name)
        if display_name is not None:
            self._display_name = display_name
        else:
            self._display_name = name

    def sizeHint(self):
        """QT event callback function"""
        return QSize(80, 105)

    def mousePressEvent(self, event):
        """QT event callback function"""
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self._name)
            drag.setMimeData(mime)
            drag.setHotSpot(event.pos() - self.rect().topLeft())
            # Create a square pixmap for dragging, using the widget's width for both dimensions.
            # This is intentional to maintain a consistent visual representation during drag operations.
            pixmap = QPixmap(self.size().width(), self.size().width())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.exec_(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)

    def mouseDoubleClickEvent(self, _):
        """QT event callback function"""
        QTimer.singleShot(0, partial(self._circuit_area.add_component, self._name, None))

    def paintEvent(self, event):
        """QT event callback function"""
        if self._paint_class is None:
            super().paintEvent(event)
        else:
            painter = QPainter(self)
            self._paint_class.paint_selectable_component(painter, self.size(), self._display_name)


class HorizontalLine(QFrame):
    """
    Horizontal line for the component selection
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class DescriptionText(QWidget):
    """
    Text label for the component selection
    """

    def __init__(self, parent, text):
        super().__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(HorizontalLine(self))
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(label)
        self.layout().addWidget(HorizontalLine(self))


class ComponentSelection(QWidget):
    """
    The component selection area,
    these are the components than can be dragged into the circuit area.
    """

    def __init__(self, app_model, circuit_area, parent):
        super().__init__(parent)
        self.app_model = app_model
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().setSpacing(5)
        self.layout().addWidget(DescriptionText(self, "Input"))
        self.layout().addWidget(SelectableComponentWidget("PushButton", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("OnOffSwitch", self, circuit_area))
        self.layout().addWidget(
            SelectableComponentWidget("DipSwitch", self, circuit_area, display_name="DIP switch")
        )
        self.layout().addWidget(SelectableComponentWidget("Clock", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("StaticValue", self, circuit_area))
        self.layout().addWidget(DescriptionText(self, "Output"))
        self.layout().addWidget(SelectableComponentWidget("Led", self, circuit_area))
        self.layout().addWidget(
            SelectableComponentWidget("HexDigit", self, circuit_area, display_name="Hex-digit")
        )
        self.layout().addWidget(
            SelectableComponentWidget("SevenSegment", self, circuit_area, display_name="7-Seg")
        )
        self.layout().addWidget(SelectableComponentWidget("Buzzer", self, circuit_area))
        self.layout().addWidget(
            SelectableComponentWidget(
                "LogicAnalyzer", self, circuit_area, display_name="Logic Analyzer"
            )
        )
        self.layout().addWidget(DescriptionText(self, "Gates"))
        self.layout().addWidget(SelectableComponentWidget("OR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("AND", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NOT", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("XOR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NAND", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("NOR", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("DFF", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("FlipFlop", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("MUX", self, circuit_area))
        self.layout().addWidget(DescriptionText(self, "Bus / Wires"))
        self.layout().addWidget(
            SelectableComponentWidget("LabelWireIn", self, circuit_area, display_name="Wire Sink")
        )
        self.layout().addWidget(
            SelectableComponentWidget(
                "LabelWireOut", self, circuit_area, display_name="Wire Source"
            )
        )
        self.layout().addWidget(SelectableComponentWidget("Bus2Wires", self, circuit_area))
        self.layout().addWidget(SelectableComponentWidget("Wires2Bus", self, circuit_area))
        self.layout().addWidget(DescriptionText(self, "IC / Verilog"))
        self.layout().addWidget(
            SelectableComponentWidget("IntegratedCircuit", self, circuit_area, display_name="IC")
        )
        self.layout().addWidget(
            SelectableComponentWidget("YosysComponent", self, circuit_area, display_name="Yosys")
        )
        self.layout().addWidget(DescriptionText(self, "Other"))
        self.layout().addWidget(SelectableComponentWidget("Note", self, circuit_area))
