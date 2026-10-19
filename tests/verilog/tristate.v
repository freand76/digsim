// Tristate outputs and a tristate bus, for tests/test_tristate.py

// An output that is not driven when OE is low
module tristate_output (
    input [3:0] a,
    input oe,
    output [3:0] y
);
   assign y = oe ? a : 4'bz;
endmodule

// Two drivers on one bus inside the design, and the bus as an output
module tristate_bus (
    input [3:0] a,
    input [3:0] b,
    input oe_a,
    input oe_b,
    output [3:0] y
);
   wire [3:0] bus;
   assign bus = oe_a ? a : 4'bz;
   assign bus = oe_b ? b : 4'bz;
   assign y = bus;
endmodule
