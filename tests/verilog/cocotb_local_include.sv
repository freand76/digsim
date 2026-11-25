// A file with a time declaration (synthesized as a copy without it) that includes a file
// from its own folder
`include "cocotb_local.vh"

module local_include (
  input  logic [`LOCAL_WIDTH-1:0] a,
  output logic [`LOCAL_WIDTH-1:0] y
);

  timeunit 1ns;

  assign y = a;

endmodule
