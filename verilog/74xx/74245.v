// Copyright (c) Fredrik Andersson, 2026
// All rights reserved

// 74245: octal bus transceiver. While OE_bar is low it drives B with A when DIR is high,
// and A with B when DIR is low. While OE_bar is high it drives neither, both sides are
// in high impedance.

module ttl_74245 (
    inout [7:0] A,
    inout [7:0] B,
    input DIR,
    input OE_bar
);
   assign B = (!OE_bar & DIR) ? A : 8'bz;
   assign A = (!OE_bar & !DIR) ? B : 8'bz;
endmodule
