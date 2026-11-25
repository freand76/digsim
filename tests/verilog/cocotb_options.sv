// Include folders, macros and parameters for the cocotb launcher tests
`include "cocotb_options.vh"

module options #(
  parameter WIDTH = 2
) (
  input  logic [WIDTH-1:0] a,
  output logic [WIDTH-1:0] y
);

`ifdef INVERT
  assign y = ~a;
`else
  assign y = a;
`endif

endmodule
