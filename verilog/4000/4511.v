// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 4511: BCD to 7-segment latch, decoder and driver, for a common-cathode display.
// The latch is transparent while LE is low and holds the value while it is high.
// LT_bar (low) turns all segments on, BI_bar (low) turns them off, and the codes 10 to
// 15 are blank. As on the real chip, 6 and 9 are drawn without tails.

module cmos_4511 (
    input [3:0] D,
    input LE,
    input BI_bar,
    input LT_bar,
    output a,
    output b,
    output c,
    output d,
    output e,
    output f,
    output g
);
   reg [3:0] latched;

   always @*
     if (!LE)
       latched = D;

   reg [6:0] segments;  // {g, f, e, d, c, b, a}

   always @*
     case (latched)
       4'd0: segments = 7'b0111111;
       4'd1: segments = 7'b0000110;
       4'd2: segments = 7'b1011011;
       4'd3: segments = 7'b1001111;
       4'd4: segments = 7'b1100110;
       4'd5: segments = 7'b1101101;
       4'd6: segments = 7'b1111100;
       4'd7: segments = 7'b0000111;
       4'd8: segments = 7'b1111111;
       4'd9: segments = 7'b1100111;
       default: segments = 7'b0000000;
     endcase

   wire [6:0] shown = !LT_bar ? 7'b1111111 : (!BI_bar ? 7'b0000000 : segments);
   assign {g, f, e, d, c, b, a} = shown;
endmodule
