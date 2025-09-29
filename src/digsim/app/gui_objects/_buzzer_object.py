# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A buzzer component object"""

from math import pi, sin
from struct import pack

from PySide6.QtCore import QByteArray, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from ._image_objects import ImageObjectWithActiveRect


class _AudioOutput(QIODevice):
    def __init__(self, audio_format, tone_hz):
        super().__init__()

        self.pos = 0
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
        self.open(QIODevice.ReadOnly)

    def readData(self, maxlen):
        """Read function"""
        data = QByteArray()
        total = 0
        while maxlen > total:
            chunk = min(self.audio_buffer.size() - self.pos, maxlen - total)
            data.append(self.audio_buffer.mid(self.pos, chunk))
            self.pos = (self.pos + chunk) % self.audio_buffer.size()
            total += chunk

        return data.data()

    def writeData(self, _):
        """Write function"""
        return 0

    def bytesAvailable(self):
        """Byteas available function"""
        return self.audio_buffer.size() + super().bytesAvailable()


class BuzzerObject(ImageObjectWithActiveRect):
    """The class for Buzzer component placed in the GUI"""

    IMAGE_FILENAME = "images/Buzzer.png"
    DATA_SAMPLE_RATE_HZ = 44100

    def __init__(self, app_model, component, xpos, ypos):
        super().__init__(app_model, component, xpos, ypos)
        self.audio_sink = None
        self._app_model.sig_audio_start.connect(self._audio_start)
        self._app_model.sig_audio_notify.connect(self._audio_notify)
        self.device = QMediaDevices.defaultAudioOutput()
        self.audio_format = QAudioFormat()
        self.audio_format.setSampleRate(self.DATA_SAMPLE_RATE_HZ)
        self.audio_format.setChannelCount(1)
        self.audio_format.setSampleFormat(QAudioFormat.Int16)
        self.audio_output = _AudioOutput(self.audio_format, self.component.tone_frequency())

    def _audio_start(self, enable):
        if enable:
            self._play(self.component.active)
        else:
            self._play(False)

    def _audio_notify(self, component):
        if component == self.component:
            self._play(component.active)

    def _play(self, active):
        if self.device is None:
            return
        if active:
            if self.audio_sink is None:
                self.audio_sink = QAudioSink(self.device, self.audio_format)
                self.audio_sink.setVolume(0.1)
            self.audio_sink.start(self.audio_output)
        else:
            if self.audio_sink is not None:
                self.audio_sink.stop()
                self.audio_sink = None
