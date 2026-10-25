module parameters #(
    parameter WIDTH = 4,
    parameter signed [7:0] OFFSET = 1,
    parameter [63:0] BIG = 0
) (
    input [WIDTH-1:0] a,
    output [WIDTH-1:0] y,
    output [7:0] offset,
    output [63:0] big
);
   assign y = a + OFFSET;
   assign offset = OFFSET;
   assign big = BIG;
endmodule
