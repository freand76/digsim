// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 7485: 4-bit magnitude comparator, cascadable with the comparison of lower bits
// (I_AgtB, I_AeqB, I_AltB). The result for equal A and B follows the datasheet table,
// also for the combinations of the cascade inputs that are not a single comparison.

module ttl_7485 (
    input [3:0] A,
    input [3:0] B,
    input I_AgtB,
    input I_AeqB,
    input I_AltB,
    output O_AgtB,
    output O_AeqB,
    output O_AltB
);
   wire equal = A == B;
   assign O_AeqB = equal & I_AeqB;
   assign O_AgtB = (A > B) | (equal & ~I_AeqB & ~I_AltB);
   assign O_AltB = (A < B) | (equal & ~I_AeqB & ~I_AgtB);
endmodule
