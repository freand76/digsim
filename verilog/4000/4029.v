// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 4029: presettable up/down counter, binary or decade. While PE is high, J is loaded
// (asynchronously). Otherwise a rising edge of CLK counts while CI_bar is low: up while
// UD is high, down while it is low, binary (0 to 15) while BD is high, decade (0 to 9)
// while it is low. CO_bar is low at the last count (15 or 9 up, 0 down) while CI_bar is
// low, for the next counter in a chain.

module cmos_4029 (
    input CLK,
    input CI_bar,
    input UD,
    input BD,
    input PE,
    input [3:0] J,
    output reg [3:0] Q,
    output CO_bar
);
   wire [3:0] top = BD ? 4'd15 : 4'd9;

   always @(posedge CLK or posedge PE)
     if (PE)
       Q <= J;
     else if (!CI_bar)
       if (UD)
         Q <= (Q >= top) ? 4'd0 : Q + 4'd1;
       else
         Q <= (Q == 4'd0) ? top : Q - 4'd1;

   assign CO_bar = CI_bar | (UD ? (Q != top) : (Q != 4'd0));
endmodule
