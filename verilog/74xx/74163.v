// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74163: synchronous 4-bit binary counter with parallel load and synchronous clear. At a
// rising edge of Clk: Clear_bar (low) clears, else Load_bar (low) loads D, else it counts
// while ENP and ENT are high. RCO is high at 15 while ENT is high. Q[0] is QA and Q[3]
// is QD of the datasheet.

module ttl_74163 (
    input Clear_bar,
    input Load_bar,
    input ENT,
    input ENP,
    input [3:0] D,
    input Clk,
    output RCO,
    output reg [3:0] Q
);
   always @(posedge Clk)
     if (!Clear_bar)
       Q <= 4'd0;
     else if (!Load_bar)
       Q <= D;
     else if (ENP & ENT)
       Q <= Q + 4'd1;

   assign RCO = ENT & (Q == 4'd15);
endmodule
