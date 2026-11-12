# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pytest module to test the buzzer tone samples"""

from itertools import pairwise

import pytest

from digsim.app._tone import tone_samples
from digsim.circuit.components import Buzzer


SAMPLE_RATE = 44100


@pytest.mark.parametrize("tone_hz", Buzzer.TONE_TO_FREQUENCY.values())
def test_tone_loops_without_jump(tone_hz):
    """The wave continues smoothly where the samples are looped"""
    samples = tone_samples(tone_hz, SAMPLE_RATE)
    largest_step = max(abs(b - a) for a, b in pairwise(samples))
    assert abs(samples[0] - samples[-1]) <= largest_step


@pytest.mark.parametrize("tone_hz", Buzzer.TONE_TO_FREQUENCY.values())
def test_tone_frequency(tone_hz):
    """About one second of samples, with the frequency of the tone"""
    samples = tone_samples(tone_hz, SAMPLE_RATE)
    assert abs(len(samples) - SAMPLE_RATE) < SAMPLE_RATE / 100
    rising_zero_crossings = sum(1 for a, b in pairwise(samples) if a < 0 <= b)
    periods = rising_zero_crossings + 1  # The wave starts at a rising zero crossing
    # A whole number of samples can shift the frequency by up to half a sample per second
    assert periods * SAMPLE_RATE / len(samples) == pytest.approx(tone_hz, abs=0.05)
