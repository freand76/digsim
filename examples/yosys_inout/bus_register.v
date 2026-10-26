// A register on a bidirectional data bus, like a memory or a peripheral on the bus of a
// CPU: it drives the bus with its value while oe is high, and stores the value on the bus
// at a rising clock edge while we is high.
module bus_register #(parameter WIDTH = 8) (
    input clk,
    input we,
    input oe,
    inout [WIDTH-1:0] data,
    output [WIDTH-1:0] value
);

   reg [WIDTH-1:0] stored;

   assign data = oe ? stored : {WIDTH{1'bz}};
   assign value = stored;

   always @(posedge clk)
     if (we)
       stored <= data;

endmodule
