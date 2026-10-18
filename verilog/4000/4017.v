// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 4017: decade counter with 10 decoded outputs. It counts on a rising clock edge while
// Clock_inhibit is low, Reset (high) goes to 0 asynchronously. Q is one-hot, Q[n] is
// high in count n. Carry_out is high in counts 0 to 4 and low in 5 to 9, its rising
// edge clocks the next 4017 every ten counts.

module cmos_4017 (
    input Clock,
    input Clock_inhibit,
    input Reset,
    output [9:0] Q,
    output Carry_out
);
   reg [3:0] count;

   always @(posedge Clock or posedge Reset)
     if (Reset)
       count <= 4'd0;
     else if (!Clock_inhibit)
       count <= count == 4'd9 ? 4'd0 : count + 4'd1;

   assign Q = 10'b1 << count;
   assign Carry_out = count < 4'd5;
endmodule
