// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

// 74182: look-ahead carry generator for four 74181 ALUs, from the datasheet equations.
// The generate and propagate inputs and outputs are active-low, the carries active-high
// (as for 74181s with active-low data, it works for both data polarities).

module ttl_74182 (
    input Cn,
    input [3:0] G_bar,
    input [3:0] P_bar,
    output Cnx,
    output Cny,
    output Cnz,
    output G_out_bar,
    output P_out_bar
);
   wire [3:0] G = ~G_bar;
   wire [3:0] P = ~P_bar;

   assign Cnx = G[0] | (P[0] & Cn);
   assign Cny = G[1] | (P[1] & G[0]) | (P[1] & P[0] & Cn);
   assign Cnz = G[2] | (P[2] & G[1]) | (P[2] & P[1] & G[0]) | (P[2] & P[1] & P[0] & Cn);
   assign G_out_bar = ~(G[3] | (P[3] & G[2]) | (P[3] & P[2] & G[1]) | (P[3] & P[2] & P[1] & G[0]));
   assign P_out_bar = ~(&P);
endmodule
