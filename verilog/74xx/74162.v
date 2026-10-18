// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74162: synchronous 4-bit decade counter with parallel load, written from the datasheet.
// At a rising edge of Clk: Clear_bar (low) clears, else Load_bar (low) loads D, else it
// counts while ENP and ENT are high. RCO is high at 9 while ENT is high, for the next
// counter in a chain. Q[0] is QA and Q[3] is QD of the datasheet.
// The flip-flops toggle like the datasheet's logic, so the counts 10 to 15 go back to
// the decade like on the real chip: 10, 11, 6 and 12, 13, 4 and 14, 15, 2.

module ttl_74162 (
    input Clear_bar,
    input Load_bar,
    input ENT,
    input ENP,
    input [3:0] D,
    input Clk,
    output RCO,
    output reg [3:0] Q
);
   // The toggles of a synchronous decade counter: QA always, QB when QA is high and QD
   // low, QC when QA and QB are high, QD when QA, QB and QC are high, or QA and QD
   wire [3:0] toggle = {
      (Q[0] & Q[1] & Q[2]) | (Q[0] & Q[3]),
      Q[0] & Q[1],
      Q[0] & ~Q[3],
      1'b1
   };

   always @(posedge Clk)
     if (!Clear_bar)
       Q <= 4'd0;
     else if (!Load_bar)
       Q <= D;
     else if (ENP & ENT)
       Q <= Q ^ toggle;

   assign RCO = ENT & Q[0] & Q[3];
endmodule
