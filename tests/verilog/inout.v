// Inout ports, for tests/test_yosys_inout.py

// Drives the inout port with a while oe is high, and reads it back to y
module inout_port (
    input [3:0] a,
    input oe,
    inout [3:0] pad,
    output [3:0] y
);
   assign pad = oe ? a : 4'bz;
   assign y = pad;
endmodule

// An output enable for each bit
module inout_bits (
    input [3:0] a,
    input [3:0] oe,
    inout [3:0] pad,
    output [3:0] y
);
   genvar i;
   generate
      for (i = 0; i < 4; i = i + 1) begin : bits
         assign pad[i] = oe[i] ? a[i] : 1'bz;
      end
   endgenerate
   assign y = pad;
endmodule

// An inout port that is only read
module inout_read (
    inout [7:0] pad,
    output [7:0] y
);
   assign y = ~pad;
endmodule

// An inout port of one bit, with constant bits next to it
module inout_constant (
    input a,
    input oe,
    inout pad,
    inout [1:0] fixed,
    output y
);
   assign pad = oe ? a : 1'bz;
   assign fixed = 2'b10;
   assign y = pad;
endmodule
