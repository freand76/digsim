// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74193: synchronous 4-bit up/down binary counter with two clocks. It counts up on a
// rising edge of Up while Down is high, and down on a rising edge of Down while Up is
// high. Clear (high) and Load_bar (low, loads D) are asynchronous. Carry_bar is low while
// Up is low at 15, Borrow_bar while Down is low at 0.

module ttl_74193 (
    input Up,
    input Down,
    input Clear,
    input Load_bar,
    input [3:0] D,
    output reg [3:0] Q,
    output Carry_bar,
    output Borrow_bar
);
   // Both clocks rise from low to high, so a count is a rising edge of (Up and Down).
   // Which one went low before tells the direction.
   wire count_clock = Up & Down;
   reg count_up;

   always @(negedge count_clock)
     count_up <= ~Up;

   always @(posedge count_clock or posedge Clear or negedge Load_bar)
     if (Clear)
       Q <= 4'd0;
     else if (!Load_bar)
       Q <= D;
     else if (count_up)
       Q <= Q + 4'd1;
     else
       Q <= Q - 4'd1;

   assign Carry_bar = ~(~Up & (Q == 4'd15));
   assign Borrow_bar = ~(~Down & (Q == 4'd0));
endmodule
