import sys

from PyQt5 import Qt, QtCore, QtGui, QtWidgets


class MyButton(QtWidgets.QPushButton):
    def __init__(self, parent, component):
        super().__init__(parent, objectName=component.name)
        self.resize(120, 100)
        self._component = component
        self._name = component.name

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        path = QtGui.QPainterPath()
        object_rect = QtCore.QRectF(event.rect())
        object_rect.setBottom(object_rect.bottom() - 1)
        object_rect.setRight(object_rect.right() - 1)
        painter.setPen(QtCore.Qt.black)
        path.addRoundedRect(object_rect, 5, 5)
        painter.setPen(QtCore.Qt.blue)
        painter.fillPath(path, QtCore.Qt.red)
        painter.drawPath(path)
        painter.setFont(QtGui.QFont("Arial", 12))
        painter.drawText(object_rect, QtCore.Qt.AlignCenter, self._name)
        painter.end()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            print(f"press {self._name}")
            self._component.onpress()
            self._component.circuit.run(ms=1)
        elif event.button() == QtCore.Qt.RightButton:
            # save the click position to keep it consistent when dragging
            self.mousePos = event.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            print(f"release {self._name}")
            self._component.onrelease()
            self._component.circuit.run(ms=1)

    def mouseMoveEvent(self, event):
        if event.buttons() != QtCore.Qt.RightButton:
            return
        mimeData = QtCore.QMimeData()
        # create a byte array and a stream that is used to write into
        byteArray = QtCore.QByteArray()
        stream = QtCore.QDataStream(byteArray, QtCore.QIODevice.WriteOnly)
        # set the objectName and click position to keep track of the widget
        # that we're moving and it's click position to ensure that it will
        # be moved accordingly
        stream.writeQString(self.objectName())
        stream.writeQVariant(self.mousePos)
        # create a custom mimeData format to save the drag info
        mimeData.setData("myApp/QtWidget", byteArray)
        drag = QtGui.QDrag(self)
        # add a pixmap of the widget to show what's actually moving
        drag.setPixmap(self.grab())
        drag.setMimeData(mimeData)
        # set the hotspot according to the mouse press position
        drag.setHotSpot(self.mousePos - self.rect().topLeft())
        drag.exec_()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app_model):
        QtWidgets.QMainWindow.__init__(self)
        super().__init__()
        self._app_model = app_model

        self.resize(800, 600)
        centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(centralWidget)
        circuit = self._app_model.circuit
        for idx, comp in enumerate(circuit.components):
            pushButton = MyButton(centralWidget, comp)
            pushButton.move(20 + 200 * idx, 20)
            self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        # only accept our mimeData format, ignoring any other data content
        if event.mimeData().hasFormat("myApp/QtWidget"):
            event.accept()

    def dropEvent(self, event):
        stream = QtCore.QDataStream(event.mimeData().data("myApp/QtWidget"))
        # QDataStream objects should be read in the same order as they were written
        objectName = stream.readQString()
        # find the child widget that has the objectName set within the drag event
        widget = self.findChild(QtWidgets.QWidget, objectName)
        if not widget:
            return
        # move the widget relative to the original mouse position, so that
        # it will be placed exactly where the user drags it and according to
        # the original click position
        widget.move(event.pos() - stream.readQVariant())
