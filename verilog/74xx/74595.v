// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74595: 8-bit shift register with an output register. A rising edge of SRCLK shifts SER
// into Q[0] (QA) and the bits towards Q[7] (QH), a rising edge of RCLK copies the shift
// register to the outputs. SRCLR_bar (low) clears the shift register asynchronously.
// QH_serial is the last bit of the shift register, for the next chip in a chain.
// OE_bar (low) enables the outputs Q, otherwise they are in high impedance and can share
// a bus with other tristate outputs. QH_serial is always enabled.

module ttl_74595 (
    input SER,
    input SRCLK,
    input SRCLR_bar,
    input RCLK,
    input OE_bar,
    output [7:0] Q,
    output QH_serial
);
   reg [7:0] shift;
   reg [7:0] latch;

   always @(posedge SRCLK or negedge SRCLR_bar)
     if (!SRCLR_bar)
       shift <= 8'd0;
     else
       shift <= {shift[6:0], SER};

   always @(posedge RCLK)
     latch <= shift;

   assign Q = OE_bar ? 8'bz : latch;

   assign QH_serial = shift[7];
endmodule
