// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74138: 3-to-8 line decoder with active-low outputs, enabled when G1 is high and
// G2A_bar and G2B_bar are low

module ttl_74138 (
    input [2:0] A,
    input G1,
    input G2A_bar,
    input G2B_bar,
    output [7:0] Y_bar
);
   wire enable = G1 & ~G2A_bar & ~G2B_bar;
   assign Y_bar = enable ? ~(8'b1 << A) : 8'hFF;
endmodule
