// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 4021: 8-stage parallel-in, serial-out shift register. While PL is high, P is loaded
// (asynchronously). While it is low, a rising edge of CP shifts DS into the first stage
// and the stages towards the last. The outputs are the last three stages, Q6, Q7 and
// Q8. P[0] is P1 and P[7] is P8 of the datasheet.

module cmos_4021 (
    input [7:0] P,
    input PL,
    input DS,
    input CP,
    output Q6,
    output Q7,
    output Q8
);
   reg [7:0] shift;

   always @(posedge CP or posedge PL)
     if (PL)
       shift <= P;
     else
       shift <= {shift[6:0], DS};

   assign Q6 = shift[5];
   assign Q7 = shift[6];
   assign Q8 = shift[7];
endmodule
