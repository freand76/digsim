// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74194: 4-bit bidirectional universal shift register. S1 and S0 select the mode at the
// rising clock edge: 00 hold, 01 shift right (towards Q[3], DSR into Q[0]), 10 shift
// left (towards Q[0], DSL into Q[3]), 11 load D. Clear_bar (low) clears asynchronously.
// Q[0] is QA and Q[3] is QD of the datasheet.

module ttl_74194 (
    input Clk,
    input Clear_bar,
    input S0,
    input S1,
    input DSR,
    input DSL,
    input [3:0] D,
    output reg [3:0] Q
);
   always @(posedge Clk or negedge Clear_bar)
     if (!Clear_bar)
       Q <= 4'd0;
     else
       case ({S1, S0})
         2'b01: Q <= {Q[2:0], DSR};
         2'b10: Q <= {DSL, Q[3:1]};
         2'b11: Q <= D;
         default: Q <= Q;
       endcase
endmodule
