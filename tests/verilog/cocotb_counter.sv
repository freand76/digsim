// A counter for the cocotb tests, with the time declarations that Yosys can't parse
module counter (
  input  logic clk,
  input  logic rst,
  input  logic ena,
  input  logic set,
  input  logic [7:0] din,
  output logic [7:0] count
);

  timeunit 1ns;
  timeprecision 1ns;

  // A named signal inside the module, for the waves
  logic [7:0] value;
  assign count = value;

  always_ff @(posedge clk) begin
    if (rst)
      value <= 8'd0;
    else if (set)
      value <= din;
    else if (ena)
      value <= value + 1;
  end

endmodule
