// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74157: quad 2-to-1 multiplexer, data selector. Y is A while S is low and B while S is
// high. G_bar (high) makes Y low.

module ttl_74157 (
    input [3:0] A,
    input [3:0] B,
    input S,
    input G_bar,
    output [3:0] Y
);
   assign Y = G_bar ? 4'd0 : (S ? B : A);
endmodule
