// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74574: octal D flip-flops with tristate outputs. A rising edge of Clk loads D. OE_bar
// (low) enables the outputs, otherwise Q is in high impedance and can share a bus.
// The 74374 is the same with another pinout.

module ttl_74574 (
    input [7:0] D,
    input Clk,
    input OE_bar,
    output [7:0] Q
);
   reg [7:0] register;

   always @(posedge Clk)
     register <= D;

   assign Q = OE_bar ? 8'bz : register;
endmodule
