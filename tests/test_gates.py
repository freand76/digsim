import pytest

from digsim import AND, NOT, Circuit, SignalLevel

UNKNOWN = SignalLevel.UNKNOWN
HIGH = SignalLevel.HIGH
LOW = SignalLevel.LOW


@pytest.mark.parametrize(
    "in_a,in_b,out_y",
    [
        (UNKNOWN, UNKNOWN, UNKNOWN),
        (LOW, UNKNOWN, LOW),
        (HIGH, UNKNOWN, UNKNOWN),
        (LOW, LOW, LOW),
        (LOW, HIGH, LOW),
        (HIGH, LOW, LOW),
        (HIGH, HIGH, HIGH),
    ],
)
def test_and(in_a, in_b, out_y):
    circuit = Circuit()
    _and = AND(circuit)

    _and.A.level = in_a
    _and.B.level = in_b
    assert _and.A.level == in_a
    assert _and.B.level == in_b
    assert _and.Y.level == UNKNOWN
    circuit.run(ms=1)
    assert _and.Y.level == out_y


@pytest.mark.parametrize(
    "in_a,out_y",
    [
        (UNKNOWN, UNKNOWN),
        (LOW, HIGH),
        (HIGH, LOW),
    ],
)
def test_not(in_a, out_y):
    circuit = Circuit()
    _not = NOT(circuit)

    _not.A.level = in_a
    assert _not.A.level == in_a
    assert _not.Y.level == UNKNOWN
    circuit.run(ms=1)
    assert _not.Y.level == out_y
