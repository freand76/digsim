// Deposits on the signals inside a design: a register, logic after it and logic after an
// input, and a signal with a constant bit and a bit of an input
module deposit (
  input  logic       clk,
  input  logic       ena,
  input  logic [3:0] a,
  output logic [3:0] y
);

  logic [3:0] count;
  logic [3:0] count_plus_one;
  logic [3:0] a_inv;
  logic [1:0] mixed;

  always_ff @(posedge clk) begin
    if (ena) count <= count + 4'd1;
  end

  assign count_plus_one = count + 4'd1;
  assign a_inv = ~a;
  assign mixed = {1'b1, a[0]};
  assign y = a_inv ^ count_plus_one;

endmodule
