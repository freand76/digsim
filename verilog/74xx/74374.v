// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74374: octal D flip-flops with tristate outputs. A rising edge of Clk loads D. OE_bar
// (low) enables the outputs, otherwise Q is in high impedance and can share a bus.
// The 74574 is the same with its inputs and outputs on opposite sides of the chip.

module ttl_74374 (
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
