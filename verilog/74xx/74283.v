// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74283: 4-bit binary full adder with fast carry

module ttl_74283 (
    input [3:0] A,
    input [3:0] B,
    input C0,
    output [3:0] S,
    output C4
);
   assign {C4, S} = A + B + C0;
endmodule
