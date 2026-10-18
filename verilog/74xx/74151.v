// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74151: 8-to-1 multiplexer with an active-low strobe, Y and the inverted W

module ttl_74151 (
    input [7:0] D,
    input [2:0] A,
    input Strobe_bar,
    output Y,
    output W
);
   assign Y = ~Strobe_bar & D[A];
   assign W = ~Y;
endmodule
