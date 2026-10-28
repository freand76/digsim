# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
Pytest module to test the bundled ICs against models of their datasheets: the netlists
in digsim/circuit/components/ic (gates), and their Verilog synthesized into functional
blocks
"""

import random
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import Bus2Wires, IntegratedCircuit, YosysComponent
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


VERILOG = Path(__file__).parent.parent / "verilog"
SOURCES = {
    "74181": ("74xx/74181.v", "ttl_74181"),
    "74182": ("74xx/74182.v", "ttl_74182"),
    "74283": ("74xx/74283.v", "ttl_74283"),
    "7485": ("74xx/7485.v", "ttl_7485"),
    "74138": ("74xx/74138.v", "ttl_74138"),
    "74151": ("74xx/74151.v", "ttl_74151"),
    "74162": ("74xx/74162.v", "ttl_74162"),
    "74164": ("74xx/74164.v", "ttl_74164"),
    "74165": ("74xx/74165.v", "ttl_74165"),
    "74193": ("74xx/74193.v", "ttl_74193"),
    "74194": ("74xx/74194.v", "ttl_74194"),
    "74595": ("74xx/74595.v", "ttl_74595"),
    "4017": ("4000/4017.v", "cmos_4017"),
    "4511": ("4000/4511.v", "cmos_4511"),
}
# The bundled gate netlist, and the Verilog synthesized into functional blocks
KINDS = ["netlist", "functional"]


def _chip(circuit, ic_name, kind):
    if kind == "netlist":
        return IntegratedCircuit(circuit, ic_name=ic_name)
    path, top = SOURCES[ic_name]
    synthesis = Synthesis([str(VERILOG / path)], top, functional=True)
    component = YosysComponent(circuit)
    component.create_from_netlist(YosysNetlist(**synthesis.synth_to_dict(silent=True)))
    return component


class Bench:
    """One chip in a circuit: set its inputs, let it settle, read its outputs"""

    def __init__(self, ic_name, kind):
        self.circuit = Circuit()
        self.chip = _chip(self.circuit, ic_name, kind)
        self.circuit.init()

    def set(self, **inputs):
        for name, value in inputs.items():
            self.chip.port(name).value = value
        self.circuit.run(us=1)

    def get(self, name):
        return self.chip.port(name).value

    def pulse(self, name, active=1):
        """A clock pulse: to the active level and back"""
        self.set(**{name: active})
        self.set(**{name: 1 - active})


# --------------------------------------------------------------------------------------
# 74181 ALU and 74182 carry look-ahead
# --------------------------------------------------------------------------------------

M4 = 0xF

# The datasheet function tables, for active-high data. Logic (M = 1): F.
LOGIC = [
    lambda a, b: ~a,
    lambda a, b: ~(a | b),
    lambda a, b: ~a & b,
    lambda a, b: 0,
    lambda a, b: ~(a & b),
    lambda a, b: ~b,
    lambda a, b: a ^ b,
    lambda a, b: a & ~b,
    lambda a, b: ~a | b,
    lambda a, b: ~(a ^ b),
    lambda a, b: b,
    lambda a, b: a & b,
    lambda a, b: M4,
    lambda a, b: a | ~b,
    lambda a, b: a | b,
    lambda a, b: a,
]
# Arithmetic (M = 0): F = X plus Y (plus 1 with a carry), "minus 1" is plus 15
ARITHMETIC = [
    lambda a, b: (a, 0),  # A
    lambda a, b: (a | b, 0),  # A + B (or)
    lambda a, b: (a | ~b, 0),  # A + not B (or)
    lambda a, b: (M4, 0),  # minus 1
    lambda a, b: (a, a & ~b),  # A plus A·not B
    lambda a, b: (a | b, a & ~b),  # (A + B) plus A·not B
    lambda a, b: (a, ~b),  # A minus B minus 1
    lambda a, b: (a & ~b, M4),  # A·not B minus 1
    lambda a, b: (a, a & b),  # A plus A·B
    lambda a, b: (a, b),  # A plus B
    lambda a, b: (a | ~b, a & b),  # (A + not B) plus A·B
    lambda a, b: (a & b, M4),  # A·B minus 1
    lambda a, b: (a, a),  # A plus A
    lambda a, b: (a | b, a),  # (A + B) plus A
    lambda a, b: (a | ~b, a),  # (A + not B) plus A
    lambda a, b: (a, M4),  # A minus 1
]


def _alu(a, b, s, m, cn):
    """F, A=B and Cn4 of the 74181 with active-high data (Cn and Cn4 active-low)"""
    if m:
        f = LOGIC[s](a, b) & M4
        cout = 1
    else:
        x, y = ARITHMETIC[s](a, b)
        total = (x & M4) + (y & M4) + (1 - cn)
        f = total & M4
        cout = 1 - (total >> 4)
    return f, int(f == M4), cout


@pytest.mark.parametrize("kind", KINDS)
def test_74181_function_table(kind):
    """All 32 functions of the datasheet, for every A and B, with and without carry"""
    bench = Bench("74181", kind)
    for s in range(16):
        for m in range(2):
            for cn in range(1 if m else 2):
                bench.set(S=s, M=m, Cn=cn)
                for a in range(16):
                    for b in range(16):
                        bench.set(A=a, B=b)
                        f, a_eq_b, cn4 = _alu(a, b, s, m, cn)
                        got = (bench.get("F"), bench.get("AeqB"))
                        assert got == (f, a_eq_b), (s, m, cn, a, b)
                        if not m:
                            assert bench.get("Cn4") == cn4, (s, cn, a, b)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("active_low", [False, True])
def test_74181_74182_16_bit(kind, active_low):
    """
    Four 74181s and a 74182 add and subtract 16-bit numbers, with active-high data (the
    carries active-low) and with active-low data (everything inverted, the carries
    active-high), as the datasheets say they work
    """
    circuit = Circuit()
    alus = [_chip(circuit, "74181", kind) for index in range(4)]
    lookahead = _chip(circuit, "74182", kind)
    # The carry look-ahead: generate and propagate from each ALU, the carries into them
    for index, alu in enumerate(alus):
        alu.G_bar.wire = lookahead.G_bar.get_bit(index)
        alu.P_bar.wire = lookahead.P_bar.get_bit(index)
    lookahead.Cnx.wire = alus[1].Cn
    lookahead.Cny.wire = alus[2].Cn
    lookahead.Cnz.wire = alus[3].Cn
    circuit.init()

    def pins(value):
        return (~value & 0xFFFF) if active_low else value

    def run(a, b, s, carry_in):
        # The carry pin: active-low with active-high data, active-high with active-low
        carry_pin = carry_in if active_low else 1 - carry_in
        for index, alu in enumerate(alus):
            alu.A.value = (pins(a) >> (4 * index)) & M4
            alu.B.value = (pins(b) >> (4 * index)) & M4
            alu.S.value = s
            alu.M.value = 0
        alus[0].Cn.value = carry_pin
        lookahead.Cn.value = carry_pin
        circuit.run(us=1)
        result = sum(alu.F.value << (4 * index) for index, alu in enumerate(alus))
        carry_out = alus[3].Cn4.value
        return pins(result), carry_out if active_low else 1 - carry_out

    rng = random.Random(7)
    for _ in range(150):
        a, b = rng.randrange(1 << 16), rng.randrange(1 << 16)
        carry = rng.randrange(2)
        # A plus B (S = 1001 in both data polarities)
        total = a + b + carry
        assert run(a, b, 0b1001, carry) == (total & 0xFFFF, total >> 16), (a, b, carry)
        # A minus B, with the carry in (S = 0110: A minus B minus 1, plus the carry)
        difference = a + (~b & 0xFFFF) + 1
        assert run(a, b, 0b0110, 1) == (difference & 0xFFFF, difference >> 16), (a, b)


@pytest.mark.parametrize("kind", KINDS)
def test_74182_equations(kind):
    """The carries, generate and propagate of the datasheet, for all inputs"""
    bench = Bench("74182", kind)
    for cn in range(2):
        for g_bar in range(16):
            for p_bar in range(16):
                bench.set(Cn=cn, G_bar=g_bar, P_bar=p_bar)
                g = [((~g_bar) >> bit) & 1 for bit in range(4)]
                p = [((~p_bar) >> bit) & 1 for bit in range(4)]
                carries = [cn]
                for bit in range(3):
                    carries.append(g[bit] | (p[bit] & carries[-1]))
                group_g = g[3] | (p[3] & g[2]) | (p[3] & p[2] & g[1]) | (p[3] & p[2] & p[1] & g[0])
                assert (bench.get("Cnx"), bench.get("Cny"), bench.get("Cnz")) == tuple(carries[1:])
                assert bench.get("G_out_bar") == 1 - group_g
                assert bench.get("P_out_bar") == 1 - (p[0] & p[1] & p[2] & p[3])


# --------------------------------------------------------------------------------------
# Adder, comparator, decoder and multiplexer
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_74283_adder(kind):
    bench = Bench("74283", kind)
    for a in range(16):
        for b in range(16):
            for c0 in range(2):
                bench.set(A=a, B=b, C0=c0)
                total = a + b + c0
                assert (bench.get("S"), bench.get("C4")) == (total & M4, total >> 4)


# The datasheet table for equal A and B: cascade inputs (>, <, =) to outputs (>, <, =)
CASCADE = {
    (1, 0, 0): (1, 0, 0),
    (0, 1, 0): (0, 1, 0),
    (0, 0, 1): (0, 0, 1),
    (1, 0, 1): (0, 0, 1),
    (0, 1, 1): (0, 0, 1),
    (1, 1, 1): (0, 0, 1),
    (1, 1, 0): (0, 0, 0),
    (0, 0, 0): (1, 1, 0),
}


@pytest.mark.parametrize("kind", KINDS)
def test_7485_comparator(kind):
    bench = Bench("7485", kind)
    for (gt, lt, eq), expected_equal in CASCADE.items():
        bench.set(I_AgtB=gt, I_AltB=lt, I_AeqB=eq)
        for a in range(16):
            for b in range(16):
                bench.set(A=a, B=b)
                got = (bench.get("O_AgtB"), bench.get("O_AltB"), bench.get("O_AeqB"))
                if a > b:
                    assert got == (1, 0, 0)
                elif a < b:
                    assert got == (0, 1, 0)
                else:
                    assert got == expected_equal, (gt, lt, eq)


@pytest.mark.parametrize("kind", KINDS)
def test_74138_decoder(kind):
    bench = Bench("74138", kind)
    for g1 in range(2):
        for g2a in range(2):
            for g2b in range(2):
                for a in range(8):
                    bench.set(A=a, G1=g1, G2A_bar=g2a, G2B_bar=g2b)
                    enabled = g1 and not g2a and not g2b
                    expected = (~(1 << a) & 0xFF) if enabled else 0xFF
                    assert bench.get("Y_bar") == expected


@pytest.mark.parametrize("kind", KINDS)
def test_74151_multiplexer(kind):
    bench = Bench("74151", kind)
    rng = random.Random(1)
    for d in [0x00, 0xFF, 0xA5, 0x5A] + [rng.randrange(256) for _ in range(8)]:
        for a in range(8):
            for strobe in range(2):
                bench.set(D=d, A=a, Strobe_bar=strobe)
                y = 0 if strobe else (d >> a) & 1
                assert (bench.get("Y"), bench.get("W")) == (y, 1 - y)


# --------------------------------------------------------------------------------------
# Counters and shift registers: random operations, compared with a model
# --------------------------------------------------------------------------------------


# The next count of the 74162 from the counts 10 to 15, from the datasheet's state diagram
DECADE_RETURN = {10: 11, 11: 6, 12: 13, 13: 4, 14: 15, 15: 2}


@pytest.mark.parametrize("kind", KINDS)
def test_74162_decade_counter(kind):
    bench = Bench("74162", kind)
    bench.set(Clk=0, Clear_bar=0, Load_bar=1, ENP=1, ENT=1, D=0)
    bench.pulse("Clk")
    bench.set(Clear_bar=1)
    count = 0
    rng = random.Random(6)
    for _ in range(400):
        clear, load = int(rng.random() > 0.05), int(rng.random() > 0.1)
        enp, ent = int(rng.random() > 0.2), int(rng.random() > 0.2)
        d = rng.randrange(16)
        bench.set(Clear_bar=clear, Load_bar=load, ENP=enp, ENT=ent, D=d)
        # The ripple carry is high at 9 (QA and QD) while ENT is high, without a clock
        assert bench.get("RCO") == int(ent and count & 0b1001 == 0b1001), count
        bench.pulse("Clk")
        # Synchronous: clear before load before counting
        if not clear:
            count = 0
        elif not load:
            count = d
        elif enp and ent:
            count = DECADE_RETURN.get(count, (count + 1) % 10)
        assert bench.get("Q") == count, (clear, load, enp, ent)


@pytest.mark.parametrize("kind", KINDS)
def test_74193_up_down_counter(kind):
    bench = Bench("74193", kind)
    bench.set(Up=1, Down=1, Load_bar=1, Clear=1)
    bench.set(Clear=0)
    count = 0
    rng = random.Random(2)
    for _ in range(300):
        operation = rng.choice(["up", "up", "down", "down", "load", "clear"])
        if operation == "up":
            bench.set(Up=0)
            # Carry_bar is low while Up is low at 15
            assert bench.get("Carry_bar") == int(count != 15)
            bench.set(Up=1)
            count = (count + 1) & M4
        elif operation == "down":
            bench.set(Down=0)
            assert bench.get("Borrow_bar") == int(count != 0)
            bench.set(Down=1)
            count = (count - 1) & M4
        elif operation == "load":
            count = rng.randrange(16)
            bench.set(D=count, Load_bar=0)
            # Asynchronous: loaded without a clock
            assert bench.get("Q") == count
            bench.set(Load_bar=1)
        else:
            bench.pulse("Clear")
            count = 0
        assert bench.get("Q") == count, operation
        assert (bench.get("Carry_bar"), bench.get("Borrow_bar")) == (1, 1)


@pytest.mark.parametrize("kind", KINDS)
def test_74194_shift_register(kind):
    bench = Bench("74194", kind)
    bench.set(Clk=0, Clear_bar=0)
    bench.set(Clear_bar=1)
    q = 0
    rng = random.Random(3)
    for _ in range(300):
        s1, s0 = rng.randrange(2), rng.randrange(2)
        dsr, dsl, d = rng.randrange(2), rng.randrange(2), rng.randrange(16)
        bench.set(S1=s1, S0=s0, DSR=dsr, DSL=dsl, D=d)
        if rng.random() < 0.05:
            bench.pulse("Clear_bar", active=0)
            q = 0
        else:
            bench.pulse("Clk")
            if (s1, s0) == (0, 1):
                q = ((q << 1) | dsr) & M4
            elif (s1, s0) == (1, 0):
                q = (q >> 1) | (dsl << 3)
            elif (s1, s0) == (1, 1):
                q = d
        assert bench.get("Q") == q, (s1, s0)


@pytest.mark.parametrize("kind", KINDS)
def test_74595_shift_register(kind):
    bench = Bench("74595", kind)
    bench.set(SRCLK=0, RCLK=0, SRCLR_bar=0, OE_bar=0)
    bench.set(SRCLR_bar=1)
    bench.pulse("RCLK")
    shift = outputs = 0
    rng = random.Random(4)
    for _ in range(400):
        operation = rng.choice(["shift", "shift", "shift", "latch", "clear"])
        if operation == "shift":
            ser = rng.randrange(2)
            bench.set(SER=ser)
            bench.pulse("SRCLK")
            shift = ((shift << 1) | ser) & 0xFF
        elif operation == "latch":
            bench.pulse("RCLK")
            outputs = shift
        else:
            bench.pulse("SRCLR_bar", active=0)
            shift = 0
        # The outputs only change with RCLK
        assert bench.get("Q") == outputs, operation
        assert bench.get("QH_serial") == shift >> 7


@pytest.mark.parametrize("kind", KINDS)
def test_74595_output_enable(kind):
    """OE_bar high puts the outputs in high impedance, the serial output stays on"""
    bench = Bench("74595", kind)
    bench.set(SRCLK=0, RCLK=0, SRCLR_bar=1, OE_bar=1, SER=1)
    assert bench.chip.Q.is_tristate()
    assert not bench.chip.QH_serial.is_tristate()
    for _ in range(8):
        bench.pulse("SRCLK")
    bench.pulse("RCLK")
    assert bench.get("Q") == "Z"
    assert bench.get("QH_serial") == 1
    bench.set(OE_bar=0)
    assert bench.get("Q") == 0xFF
    bench.set(OE_bar=1)
    assert bench.get("Q") == "Z"


@pytest.mark.parametrize("kind", KINDS)
def test_74595_shared_bus(kind):
    """Two 74595 on one bus, the one with its outputs enabled drives it"""
    circuit = Circuit()
    chips = [_chip(circuit, "74595", kind) for i in range(2)]
    bus = Bus2Wires(circuit, "bus", width=8)
    for chip in chips:
        chip.Q.wire = bus.bus
    circuit.init()
    # Shift 0xA5 into U0 and 0x3C into U1, and latch them
    for chip, value in zip(chips, (0xA5, 0x3C), strict=True):
        chip.SRCLR_bar.value = 1
        chip.OE_bar.value = 1
        for bit in range(7, -1, -1):
            chip.SER.value = (value >> bit) & 1
            chip.SRCLK.value = 1
            circuit.run(us=1)
            chip.SRCLK.value = 0
            circuit.run(us=1)
        chip.RCLK.value = 1
        circuit.run(us=1)
        chip.RCLK.value = 0
        circuit.run(us=1)
    for oe0, oe1, expected in [(0, 1, 0xA5), (1, 0, 0x3C), (1, 1, "Z"), (0, 0, "X")]:
        chips[0].OE_bar.value = oe0
        chips[1].OE_bar.value = oe1
        circuit.run(us=1)
        assert bus.bus.value == expected, (oe0, oe1)


@pytest.mark.parametrize("kind", KINDS)
def test_4017_decade_counter(kind):
    bench = Bench("4017", kind)
    bench.set(Clock=0, Clock_inhibit=0)
    bench.pulse("Reset")
    count = 0
    rng = random.Random(5)
    for _ in range(200):
        operation = rng.choice(["clock"] * 6 + ["inhibited", "reset"])
        if operation == "clock":
            bench.pulse("Clock")
            count = (count + 1) % 10
        elif operation == "inhibited":
            bench.set(Clock_inhibit=1)
            bench.pulse("Clock")
            bench.set(Clock_inhibit=0)
        else:
            bench.pulse("Reset")
            count = 0
        assert bench.get("Q") == 1 << count, operation
        assert bench.get("Carry_out") == int(count < 5)


# The segments {g, f, e, d, c, b, a} of the 4511, without tails on 6 and 9, blank above 9
SEGMENTS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7C, 0x07, 0x7F, 0x67] + [0] * 6


def _segments(bench):
    return sum(bench.get(name) << bit for bit, name in enumerate("abcdefg"))


@pytest.mark.parametrize("kind", KINDS)
def test_4511_display_driver(kind):
    bench = Bench("4511", kind)
    bench.set(LE=0, BI_bar=1, LT_bar=1)
    for value in range(16):
        bench.set(D=value)
        assert _segments(bench) == SEGMENTS[value], value
    # The latch holds the value while LE is high
    bench.set(D=3)
    bench.set(LE=1)
    bench.set(D=8)
    assert _segments(bench) == SEGMENTS[3]
    bench.set(LE=0)
    assert _segments(bench) == SEGMENTS[8]
    # Blanking turns all segments off, the lamp test all on, also while blanked
    bench.set(BI_bar=0)
    assert _segments(bench) == 0
    bench.set(LT_bar=0)
    assert _segments(bench) == 0x7F
    bench.set(BI_bar=1)
    assert _segments(bench) == 0x7F


@pytest.mark.parametrize("kind", KINDS)
def test_74164(kind):
    """Serial in, A and B, shifted towards QH; a low Clear_bar clears"""
    bench = Bench("74164", kind)
    bench.set(Clk=0, Clear_bar=0)
    bench.set(Clear_bar=1)
    expected = 0
    for bit in [1, 0, 1, 1, 0, 0, 1, 0, 1]:
        bench.set(A=bit, B=1)
        bench.pulse("Clk")
        expected = ((expected << 1) | bit) & 0xFF
        assert bench.get("Q") == expected
    # B low blocks A
    bench.set(A=1, B=0)
    bench.pulse("Clk")
    assert bench.get("Q") == (expected << 1) & 0xFF
    bench.set(Clear_bar=0)
    assert bench.get("Q") == 0


@pytest.mark.parametrize("kind", KINDS)
def test_74165(kind):
    """Load in parallel, then shift out of QH, the highest bit first"""
    bench = Bench("74165", kind)
    bench.set(Clk=0, Clk_inh=0, SER=0, D=0xB4, SH_LD_bar=0)
    bench.set(SH_LD_bar=1)
    out = []
    for _ in range(8):
        out.append(bench.get("QH"))
        assert bench.get("QH_bar") == 1 - out[-1]
        bench.pulse("Clk")
    assert out == [(0xB4 >> bit) & 1 for bit in range(7, -1, -1)]
    # Clk_inh high holds the register
    bench.set(SH_LD_bar=0)
    bench.set(SH_LD_bar=1, Clk_inh=1)
    bench.pulse("Clk")
    assert bench.get("QH") == 1
