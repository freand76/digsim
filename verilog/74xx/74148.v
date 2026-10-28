// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74148: 8-to-3 priority encoder, active low. While EI_bar is low, A_bar is the inverted
// number of the highest input of I_bar that is low, and GS_bar is low. When no input is
// low, A_bar is 7 (all high), GS_bar is high and EO_bar is low, to enable the next
// encoder in a chain. While EI_bar is high all outputs are high.

module ttl_74148 (
    input [7:0] I_bar,
    input EI_bar,
    output reg [2:0] A_bar,
    output GS_bar,
    output EO_bar
);
   wire any = ~&I_bar;

   always @(*)
     if (EI_bar)
       A_bar = 3'd7;
     else
     casez (I_bar)
       8'b0???????: A_bar = 3'd0;
       8'b10??????: A_bar = 3'd1;
       8'b110?????: A_bar = 3'd2;
       8'b1110????: A_bar = 3'd3;
       8'b11110???: A_bar = 3'd4;
       8'b111110??: A_bar = 3'd5;
       8'b1111110?: A_bar = 3'd6;
       default: A_bar = 3'd7;
     endcase

   assign GS_bar = EI_bar | ~any;
   assign EO_bar = EI_bar | any;
endmodule
