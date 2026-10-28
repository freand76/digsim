// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74139: dual 2-to-4 line decoder, active-low outputs. In each half, the output that A
// selects is low while G_bar is low, all outputs are high while G_bar is high.

module ttl_74139 (
    input G1_bar,
    input [1:0] A1,
    output [3:0] Y1_bar,
    input G2_bar,
    input [1:0] A2,
    output [3:0] Y2_bar
);
   assign Y1_bar = G1_bar ? 4'b1111 : ~(4'b0001 << A1);
   assign Y2_bar = G2_bar ? 4'b1111 : ~(4'b0001 << A2);
endmodule
