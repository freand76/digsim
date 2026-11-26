// Ranges, signed values and a constant, for the cocotb tests
module types (
  input  logic              [0:3]  up,
  input  logic signed       [7:0]  s,
  input  logic              [11:4] down,
  output logic signed       [7:0]  y
);

  logic [3:0] constant_reg;
  logic [0:3] up_copy;

  initial constant_reg = 4'b0101;

  assign up_copy = up;
  assign y = s + $signed(down);

endmodule
