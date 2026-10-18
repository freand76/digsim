// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74595: 8-bit shift register with an output register. A rising edge of SRCLK shifts SER
// into Q[0] (QA) and the bits towards Q[7] (QH), a rising edge of RCLK copies the shift
// register to the outputs. SRCLR_bar (low) clears the shift register asynchronously.
// QH_serial is the last bit of the shift register, for the next chip in a chain.
// The output enable of the real chip, with outputs in high impedance, is left out:
// DigSim has no high impedance, the outputs are always on.

module ttl_74595 (
    input SER,
    input SRCLK,
    input SRCLR_bar,
    input RCLK,
    output reg [7:0] Q,
    output QH_serial
);
   reg [7:0] shift;

   always @(posedge SRCLK or negedge SRCLR_bar)
     if (!SRCLR_bar)
       shift <= 8'd0;
     else
       shift <= {shift[6:0], SER};

   always @(posedge RCLK)
     Q <= shift;

   assign QH_serial = shift[7];
endmodule
