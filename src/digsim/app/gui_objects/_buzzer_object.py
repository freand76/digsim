# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A buzzer component object"""

from __future__ import annotations

from struct import pack
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QIODevice, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPainterPath
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from digsim.app._tone import tone_samples
from digsim.circuit.components import Buzzer
from digsim.circuit.components.atoms import Component

from . import _theme as theme
from ._device_objects import DeviceObject
from ._symbol_objects import paint_icon, port_dots


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class _AudioOutput(QIODevice):
    def __init__(self, audio_format: QAudioFormat, tone_hz: float) -> None:
        super().__init__()

        self._pos = 0
        self.audio_buffer = QByteArray()
        self.audio_buffer.clear()

        for sample in tone_samples(tone_hz, audio_format.sampleRate()):
            packed = pack("<h", sample)
            for _ in range(audio_format.channelCount()):
                self.audio_buffer.append(packed)
        self.open(QIODevice.OpenModeFlag.ReadOnly)

    def readData(self, maxlen: int) -> bytes | bytearray | memoryview:
        """Read function"""
        data = QByteArray()
        total = 0
        while maxlen > total:
            chunk = min(self.audio_buffer.size() - self._pos, maxlen - total)
            data.append(self.audio_buffer.mid(self._pos, chunk))
            self._pos = (self._pos + chunk) % self.audio_buffer.size()
            total += chunk

        return data.data()

    def writeData(self, _data: bytes | bytearray | memoryview, _len: int = 0) -> int:
        """Write function"""
        return 0

    def bytesAvailable(self) -> int:
        """Byteas available function"""
        return self.audio_buffer.size() + super().bytesAvailable()


class BuzzerObject(DeviceObject):
    """The class for Buzzer component placed in the GUI"""

    SHOW_PORT_NAMES = False
    DATA_SAMPLE_RATE_HZ = 44100

    def __init__(
        self, app_model: AppModel, component: Component, xpos: float, ypos: float
    ) -> None:
        super().__init__(app_model, component, xpos, ypos)
        self.audio_sink: QAudioSink | None = None
        self.device = QMediaDevices.defaultAudioOutput()
        self.audio_format = QAudioFormat()
        self.audio_format.setSampleRate(self.DATA_SAMPLE_RATE_HZ)
        self.audio_format.setChannelCount(1)
        self.audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._tone_hz = self.component.tone_frequency()
        self.audio_output = _AudioOutput(self.audio_format, self._tone_hz)

    @classmethod
    def paint_face(cls, painter: QPainter, rect: QRectF, active: bool) -> None:
        """A speaker, with sound waves in green while it sounds"""
        center = rect.center() - QPointF(4, 0)
        speaker = QPainterPath(QPointF(center.x() - 9, center.y() - 4))
        speaker.lineTo(center.x() - 4, center.y() - 4)
        speaker.lineTo(center.x() + 2, center.y() - 10)
        speaker.lineTo(center.x() + 2, center.y() + 10)
        speaker.lineTo(center.x() - 4, center.y() + 4)
        speaker.lineTo(center.x() - 9, center.y() + 4)
        speaker.closeSubpath()
        painter.setPen(theme.ink_pen())
        painter.setBrush(theme.INK)
        painter.drawPath(speaker)
        painter.setPen(theme.ink_pen(theme.SYMBOL_WIDTH, theme.ON if active else theme.OFF))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for radius in (6.0, 11.0):
            painter.drawArc(
                QRectF(center.x() + 2 - radius, center.y() - radius, 2 * radius, 2 * radius),
                -45 * 16,
                90 * 16,
            )

    @classmethod
    def paint_selectable_component(cls, painter: QPainter, size: QSize, name: str) -> None:
        def paint(rect: QRectF) -> None:
            theme.paint_body(painter, rect)
            cls.paint_face(painter, rect, True)
            port_dots(painter, [QPointF(rect.left() - 1, rect.center().y())])

        paint_icon(painter, size, cls.SIZE, paint, scale=1.3)
        cls.paint_selectable_component_name(painter, QPointF(0, 0), size, name)

    @property
    def component(self) -> Buzzer:
        component = self._component
        assert isinstance(component, Buzzer)
        return component

    def disconnect(self) -> None:
        self._play(False)
        super().disconnect()

    def audio_start(self, enable: bool) -> None:
        """Called when the simulation is started or stopped"""
        if enable:
            self._play(self.component.active)
        else:
            self._play(False)

    def audio_notify(self) -> None:
        """Called when the buzzer component has changed"""
        self._play(self.component.active)

    def _play(self, active: bool) -> None:
        if self.device is None:
            return
        if active:
            if self._tone_hz != self.component.tone_frequency():
                # The tone has been changed in the component settings
                self._tone_hz = self.component.tone_frequency()
                self.audio_output = _AudioOutput(self.audio_format, self._tone_hz)
            if self.audio_sink is None:
                audio_sink = QAudioSink(self.device, self.audio_format)
                audio_sink.setVolume(0.1)
                self.audio_sink = audio_sink
            self.audio_sink.start(self.audio_output)
        else:
            if self.audio_sink is not None:
                self.audio_sink.stop()
                self.audio_sink = None
