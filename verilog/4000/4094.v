// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 4094: 8-stage shift-and-store bus register. A rising edge of CP shifts D into the first
// stage and the stages towards the last. The storage latch follows the shift register
// while STR is high, and holds while it is low. OE (high) enables the outputs Q,
// otherwise they are in high impedance. QS1 is the last stage, QS2 the last stage a
// falling edge later, for chips in a chain with a slow clock. Q[0] is Q1 and Q[7] is Q8
// of the datasheet.

module cmos_4094 (
    input D,
    input CP,
    input STR,
    input OE,
    output [7:0] Q,
    output QS1,
    output reg QS2
);
   reg [7:0] shift;
   reg [7:0] store;

   always @(posedge CP)
     shift <= {shift[6:0], D};

   always @(*)
     if (STR)
       store = shift;

   always @(negedge CP)
     QS2 <= shift[7];

   assign Q = OE ? store : 8'bz;
   assign QS1 = shift[7];
endmodule
