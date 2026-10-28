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
from digsim.circuit.components import (
    Bus2Wires,
    IntegratedCircuit,
    Probe,
    StaticValue,
    TristateBuffer,
    YosysComponent,
)
from digsim.synth import Synthesis
from digsim.utils import YosysNetlist


# Also on the other platforms: the minimal scope of the tests (see .github/workflows)
pytestmark = pytest.mark.sanity


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
    "4021": ("4000/4021.v", "cmos_4021"),
    "4029": ("4000/4029.v", "cmos_4029"),
    "4094": ("4000/4094.v", "cmos_4094"),
    "74139": ("74xx/74139.v", "ttl_74139"),
    "74148": ("74xx/74148.v", "ttl_74148"),
    "74157": ("74xx/74157.v", "ttl_74157"),
    "74161": ("74xx/74161.v", "ttl_74161"),
    "74163": ("74xx/74163.v", "ttl_74163"),
    "74173": ("74xx/74173.v", "ttl_74173"),
    "74245": ("74xx/74245.v", "ttl_74245"),
    "74374": ("74xx/74374.v", "ttl_74374"),
    "74574": ("74xx/74574.v", "ttl_74574"),
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
    bench.set(Clk=0, Clk_inh=0, SER=0, D=0x01, SH_LD_bar=0)
    # While loading, the register follows D
    bench.set(D=0xB4)
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


# --------------------------------------------------------------------------------------
# More counters, registers, selectors and shift registers
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("ic_name", ["74161", "74163"])
def test_74161_74163_binary_counter(kind, ic_name):
    """The 74161 clears at once, the 74163 at the next clock edge"""
    bench = Bench(ic_name, kind)
    bench.set(Clk=0, Clear_bar=0, Load_bar=1, ENP=1, ENT=1, D=0)
    bench.pulse("Clk")
    bench.set(Clear_bar=1)
    count = 0
    rng = random.Random(7)
    for _ in range(400):
        clear, load = int(rng.random() > 0.05), int(rng.random() > 0.1)
        enp, ent = int(rng.random() > 0.2), int(rng.random() > 0.2)
        d = rng.randrange(16)
        bench.set(Clear_bar=clear, Load_bar=load, ENP=enp, ENT=ent, D=d)
        if not clear and ic_name == "74161":
            count = 0
            assert bench.get("Q") == 0
        assert bench.get("RCO") == int(ent and count == 15), count
        bench.pulse("Clk")
        if not clear:
            count = 0
        elif not load:
            count = d
        elif enp and ent:
            count = (count + 1) & M4
        assert bench.get("Q") == count, (clear, load, enp, ent)


@pytest.mark.parametrize("kind", KINDS)
def test_74157_quad_mux(kind):
    bench = Bench("74157", kind)
    rng = random.Random(8)
    for _ in range(100):
        a, b, s, g = rng.randrange(16), rng.randrange(16), rng.randrange(2), rng.randrange(2)
        bench.set(A=a, B=b, S=s, G_bar=g)
        assert bench.get("Y") == (0 if g else b if s else a)


@pytest.mark.parametrize("kind", KINDS)
def test_74173_register(kind):
    bench = Bench("74173", kind)
    bench.set(Clk=0, CLR=1, G1_bar=0, G2_bar=0, M=0, N=0, D=0)
    bench.set(CLR=0)
    register = 0
    rng = random.Random(9)
    for _ in range(200):
        d, g1, g2 = rng.randrange(16), rng.randrange(2), rng.randrange(2)
        m, n = int(rng.random() > 0.8), int(rng.random() > 0.8)
        bench.set(D=d, G1_bar=g1, G2_bar=g2, M=m, N=n)
        if rng.random() > 0.9:
            bench.pulse("CLR")
            register = 0
        else:
            bench.pulse("Clk")
            if not g1 and not g2:
                register = d
        assert bench.get("Q") == ("Z" if m or n else register)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("ic_name", ["74374", "74574"])
def test_74374_74574_octal_flip_flops(kind, ic_name):
    bench = Bench(ic_name, kind)
    bench.set(Clk=0, OE_bar=0, D=0)
    rng = random.Random(10)
    register = None
    for _ in range(100):
        d, oe = rng.randrange(256), int(rng.random() > 0.7)
        bench.set(D=d, OE_bar=oe)
        if rng.random() > 0.3:
            bench.pulse("Clk")
            register = d
        if register is not None:
            assert bench.get("Q") == ("Z" if oe else register)


@pytest.mark.parametrize("kind", KINDS)
def test_74245_bus_transceiver(kind):
    """A to B or B to A by DIR, neither while OE_bar is high"""
    circuit = Circuit()
    chip = _chip(circuit, "74245", kind)
    side_a = TristateBuffer(circuit, "drive_a", width=8)
    side_b = TristateBuffer(circuit, "drive_b", width=8)
    controls = {}
    for name, buffer, value in (("a", side_a, 0x5A), ("b", side_b, 0xC3)):
        StaticValue(circuit, f"value_{name}", width=8, value=value).O.wire = buffer.A
        controls[name] = StaticValue(circuit, f"enable_{name}", value=0)
        controls[name].O.wire = buffer.OE
    for port, buffer in ((chip.A, side_a), (chip.B, side_b)):
        buffer.Y.wire = port
    probes = {"a": Probe(circuit, "probe_a", width=8), "b": Probe(circuit, "probe_b", width=8)}
    chip.A.wire = probes["a"].I
    chip.B.wire = probes["b"].I
    side_a.Y.wire = probes["a"].I
    side_b.Y.wire = probes["b"].I
    dir_, oe = StaticValue(circuit, "dir", value=1), StaticValue(circuit, "oe", value=0)
    dir_.O.wire = chip.DIR
    oe.O.wire = chip.OE_bar
    circuit.init()

    def run(**values):
        for name, value in values.items():
            component = {"dir": dir_, "oe": oe, **controls}[name]
            component.parameter_set("value", value)
            component.reconfigure()
        circuit.run(us=1)
        return probes["a"].I.value, probes["b"].I.value

    # A drives the chip's A side, the chip drives B
    assert run(a=1, b=0, dir=1, oe=0) == (0x5A, 0x5A)
    # B to A
    assert run(a=0, b=1, dir=0) == (0xC3, 0xC3)
    # Not enabled: only B is driven, by its buffer
    assert run(oe=1) == ("Z", 0xC3)


@pytest.mark.parametrize("kind", KINDS)
def test_74148_priority_encoder(kind):
    bench = Bench("74148", kind)
    for ei in (0, 1):
        for inputs in range(256):
            bench.set(I_bar=inputs, EI_bar=ei)
            low = [bit for bit in range(8) if not inputs >> bit & 1]
            if ei:
                expected = (7, 1, 1)
            elif not low:
                expected = (7, 1, 0)
            else:
                expected = (~max(low) & 7, 0, 1)
            assert (bench.get("A_bar"), bench.get("GS_bar"), bench.get("EO_bar")) == expected


@pytest.mark.parametrize("kind", KINDS)
def test_74139_dual_decoder(kind):
    bench = Bench("74139", kind)
    for g1 in (0, 1):
        for a1 in range(4):
            for g2 in (0, 1):
                for a2 in range(4):
                    bench.set(G1_bar=g1, A1=a1, G2_bar=g2, A2=a2)
                    assert bench.get("Y1_bar") == (0xF if g1 else 0xF & ~(1 << a1))
                    assert bench.get("Y2_bar") == (0xF if g2 else 0xF & ~(1 << a2))


@pytest.mark.parametrize("kind", KINDS)
def test_4094_shift_and_store(kind):
    bench = Bench("4094", kind)
    bench.set(CP=0, STR=0, OE=1, D=0)
    for _ in range(8):
        bench.pulse("CP")
    bench.pulse("STR")
    shift = stored = 0
    serial2 = 0
    rng = random.Random(11)
    for _ in range(300):
        operation = rng.choice(["shift", "shift", "store", "oe"])
        if operation == "shift":
            d = rng.randrange(2)
            bench.set(D=d, CP=1)
            shift = ((shift << 1) | d) & 0xFF
            assert bench.get("QS2") == serial2
            bench.set(CP=0)
            serial2 = shift >> 7
        elif operation == "store":
            bench.pulse("STR")
            stored = shift
        else:
            bench.set(OE=1 - bench.get("OE"))
        assert bench.get("Q") == (stored if bench.get("OE") else "Z"), operation
        assert bench.get("QS1") == shift >> 7
        assert bench.get("QS2") == serial2


@pytest.mark.parametrize("kind", KINDS)
def test_4021_parallel_in_serial_out(kind):
    bench = Bench("4021", kind)
    bench.set(CP=0, DS=0, P=0b1011_0010, PL=1)
    bench.set(PL=0)
    shift = 0b1011_0010
    rng = random.Random(12)
    for _ in range(50):
        ds = rng.randrange(2)
        bench.set(DS=ds)
        bench.pulse("CP")
        shift = ((shift << 1) | ds) & 0xFF
        outputs = (bench.get("Q6"), bench.get("Q7"), bench.get("Q8"))
        assert outputs == (shift >> 5 & 1, shift >> 6 & 1, shift >> 7)


@pytest.mark.parametrize("kind", KINDS)
def test_4029_up_down_counter(kind):
    bench = Bench("4029", kind)
    bench.set(CLK=0, CI_bar=0, UD=1, BD=1, J=0, PE=1)
    bench.set(PE=0)
    count = 0
    rng = random.Random(13)
    for _ in range(400):
        ci, ud, bd = int(rng.random() > 0.8), rng.randrange(2), rng.randrange(2)
        top = 15 if bd else 9
        if not bd and count > 9:
            # Back in the decade first, from a binary count
            bench.set(PE=1, J=0)
            bench.set(PE=0)
            count = 0
        bench.set(CI_bar=ci, UD=ud, BD=bd)
        last = count == (top if ud else 0)
        assert bench.get("CO_bar") == int(ci or not last), (count, ud, bd)
        if rng.random() > 0.95:
            j = rng.randrange(top + 1)
            bench.set(J=j, PE=1)
            bench.set(PE=0)
            count = j
        else:
            bench.pulse("CLK")
            if not ci:
                count = (count + 1) % (top + 1) if ud else (count - 1) % (top + 1)
        assert bench.get("Q") == count
