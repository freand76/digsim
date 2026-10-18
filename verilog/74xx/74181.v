// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74181: 4-bit arithmetic logic unit, written from the datasheet function tables.
// With active-high data, Cn and Cn4 are active-low carries (1 = no carry). M = 1 gives the
// 16 logic functions, M = 0 the 16 arithmetic functions, selected by S.
// AeqB is high when F is all ones (an open-collector output on the real chip).
// G_bar and P_bar are the carry generate and propagate outputs of the datasheet, which
// defines them for active-low data: for a 74182 they work with either data polarity.

module ttl_74181 (
    input [3:0] A,
    input [3:0] B,
    input [3:0] S,
    input M,
    input Cn,
    output [3:0] F,
    output AeqB,
    output G_bar,
    output P_bar,
    output Cn4
);
   // Per bit, with active-high data: F = Pa plus Ga (plus carry) in arithmetic mode,
   // and F = not (Pa xor Ga) in logic mode
   wire [3:0] Pa = A | (B & {4{S[0]}}) | (~B & {4{S[1]}});
   wire [3:0] Ga = (A & ~B & {4{S[2]}}) | (A & B & {4{S[3]}});

   wire carry_in = ~Cn;
   wire [4:0] sum = Pa + Ga + carry_in;

   // Carry generate and propagate of the addition, with active-high data
   wire generate_hi = Ga[3] | (Pa[3] & Ga[2]) | (Pa[3] & Pa[2] & Ga[1]) | (Pa[3] & Pa[2] & Pa[1] & Ga[0]);
   wire propagate_hi = &Pa;

   assign F = M ? ~(Pa ^ Ga) : sum[3:0];
   assign Cn4 = ~(generate_hi | (propagate_hi & carry_in));
   assign AeqB = &F;
   // The datasheet pins are generate and propagate for active-low data. Inverting all
   // data and carries, the carry out is not (generate or propagate and carry in) =
   // (not generate and not propagate) or (not generate and inverted carry in): the
   // generate for active-low data is not (generate or propagate), and the propagate is
   // not generate, so the active-low pins are these
   assign G_bar = generate_hi | propagate_hi;
   assign P_bar = generate_hi;
endmodule
