// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74165: 8-bit parallel-in, serial-out shift register. While SH_LD_bar is low, D is
// loaded (asynchronously). While it is high, a rising edge of Clk shifts the bits from
// D[0] (A) towards D[7] (H), and SER into the first bit, unless Clk_inh is high.
// QH is the last bit, QH_bar its inverse.

module ttl_74165 (
    input SER,
    input Clk,
    input Clk_inh,
    input SH_LD_bar,
    input [7:0] D,
    output QH,
    output QH_bar
);
   reg [7:0] shift;

   always @(posedge Clk or negedge SH_LD_bar)
     if (!SH_LD_bar)
       shift <= D;
     else if (!Clk_inh)
       shift <= {shift[6:0], SER};

   assign QH = shift[7];
   assign QH_bar = ~shift[7];
endmodule
