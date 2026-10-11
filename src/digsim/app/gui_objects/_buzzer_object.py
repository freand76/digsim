# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A buzzer component object"""

from __future__ import annotations

from math import pi, sin
from struct import pack
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from digsim.circuit.components import Buzzer
from digsim.circuit.components.atoms import Component

from ._image_objects import ImageObjectWithActiveRect


if TYPE_CHECKING:
    from digsim.app.model import AppModel


class _AudioOutput(QIODevice):
    def __init__(self, audio_format: QAudioFormat, tone_hz: float) -> None:
        super().__init__()

        self._pos = 0
        self.audio_buffer = QByteArray()
        self.audio_buffer.clear()

        factor = 2 * pi * tone_hz / audio_format.sampleRate()
        channel_bytes = audio_format.bytesPerSample()
        length = audio_format.sampleRate() * audio_format.channelCount() * channel_bytes

        sample_index = 0
        while length > 0:
            x = 32767 * sin((sample_index % audio_format.sampleRate()) * factor)
            packed = pack("<h", int(x))
            for _ in range(audio_format.channelCount()):
                self.audio_buffer.append(packed)
                length -= channel_bytes
            sample_index += 1
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


class BuzzerObject(ImageObjectWithActiveRect):
    """The class for Buzzer component placed in the GUI"""

    IMAGE_FILENAME = "images/Buzzer.png"
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
        self.audio_output = _AudioOutput(self.audio_format, self.component.tone_frequency())

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
            if self.audio_sink is None:
                audio_sink = QAudioSink(self.device, self.audio_format)
                audio_sink.setVolume(0.1)
                self.audio_sink = audio_sink
            self.audio_sink.start(self.audio_output)
        else:
            if self.audio_sink is not None:
                self.audio_sink.stop()
                self.audio_sink = None
