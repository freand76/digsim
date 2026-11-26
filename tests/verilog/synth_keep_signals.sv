// Logic that no output depends on: synthesis removes it, unless the signals are kept
module keep_adder (
  input  logic [3:0] a,
  output logic [3:0] y
);

  assign y = a + 4'd2;

endmodule

module keep_signals (
  input  logic clk,
  input  logic rst,
  output logic y
);

  logic [3:0] count;
  logic [3:0] count_plus_two;

  always_ff @(posedge clk) begin
    if (rst) count <= 4'd0;
    else count <= count + 4'd1;
  end

  keep_adder u_add (
    .a(count),
    .y(count_plus_two)
  );

  assign y = 1'b0;

endmodule
