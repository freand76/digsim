// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74161: synchronous 4-bit binary counter with parallel load. Clear_bar (low) clears
// asynchronously. At a rising edge of Clk: Load_bar (low) loads D, else it counts while
// ENP and ENT are high. RCO is high at 15 while ENT is high, for the next counter in a
// chain. Q[0] is QA and Q[3] is QD of the datasheet.

module ttl_74161 (
    input Clear_bar,
    input Load_bar,
    input ENT,
    input ENP,
    input [3:0] D,
    input Clk,
    output RCO,
    output reg [3:0] Q
);
   always @(posedge Clk or negedge Clear_bar)
     if (!Clear_bar)
       Q <= 4'd0;
     else if (!Load_bar)
       Q <= D;
     else if (ENP & ENT)
       Q <= Q + 4'd1;

   assign RCO = ENT & (Q == 4'd15);
endmodule
