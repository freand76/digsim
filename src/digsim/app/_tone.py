# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
The samples of a buzzer tone
(kept free from Qt imports so that it can be tested without a display)
"""

from math import pi, sin


def tone_samples(tone_hz: float, sample_rate: int) -> list[int]:
    """
    About one second of a sine tone, as 16-bit samples.
    The samples hold a whole number of periods, so that the sound can be looped
    without a jump in the wave (heard as a click).
    """
    periods = max(1, round(tone_hz))
    sample_count = round(periods * sample_rate / tone_hz)
    factor = 2 * pi * periods / sample_count
    return [int(32767 * sin(index * factor)) for index in range(sample_count)]
