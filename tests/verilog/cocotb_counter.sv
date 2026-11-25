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

  always_ff @(posedge clk) begin
    if (rst)
      count <= 8'd0;
    else if (set)
      count <= din;
    else if (ena)
      count <= count + 1;
  end

endmodule
