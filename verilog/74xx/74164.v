// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74164: 8-bit serial-in, parallel-out shift register. A rising edge of Clk shifts
// A AND B into Q[0] (QA) and the bits towards Q[7] (QH). Clear_bar (low) clears
// asynchronously.

module ttl_74164 (
    input A,
    input B,
    input Clk,
    input Clear_bar,
    output reg [7:0] Q
);
   always @(posedge Clk or negedge Clear_bar)
     if (!Clear_bar)
       Q <= 8'd0;
     else
       Q <= {Q[6:0], A & B};
endmodule
