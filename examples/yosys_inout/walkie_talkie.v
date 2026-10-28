// A walkie-talkie on a shared 4-bit bus, for
// circuits/bidirectional_port/bidirectional_port.circuit.
// While talk is pressed it sends its message (the switches m0 to m3) on the bus, and it
// always shows what is on the bus on heard. The bus is an inout port: the same wire
// carries the message both ways, from whichever walkie-talkie talks.
module walkie_talkie (
    input m0,
    input m1,
    input m2,
    input m3,
    input talk,
    output [3:0] heard,
    inout [3:0] bus
);

   assign bus = talk ? {m3, m2, m1, m0} : 4'bz;
   assign heard = bus;

endmodule
