// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74173: 4-bit D register with tristate outputs. At a rising edge of Clk, D is loaded
// while G1_bar and G2_bar are low, otherwise the register holds. CLR (high) clears
// asynchronously. M and N (both low) enable the outputs, otherwise Q is in high
// impedance and can share a bus.

module ttl_74173 (
    input [3:0] D,
    input Clk,
    input CLR,
    input G1_bar,
    input G2_bar,
    input M,
    input N,
    output [3:0] Q
);
   reg [3:0] register;

   always @(posedge Clk or posedge CLR)
     if (CLR)
       register <= 4'd0;
     else if (!G1_bar & !G2_bar)
       register <= D;

   assign Q = (M | N) ? 4'bz : register;
endmodule
