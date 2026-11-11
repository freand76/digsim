// A top module made from two submodules

module half_adder (
    input  a,
    input  b,
    output s,
    output c
);
  assign s = a ^ b;
  assign c = a & b;
endmodule

module adder #(
    parameter WIDTH = 2
) (
    input  [WIDTH-1:0] x,
    input  [WIDTH-1:0] y,
    output [  WIDTH:0] sum
);
  assign sum = x + y;
endmodule

module top (
    input        a,
    input        b,
    input  [3:0] x,
    output       s,
    output       c,
    output [4:0] sum
);
  half_adder ha (
      .a(a),
      .b(b),
      .s(s),
      .c(c)
  );
  adder #(
      .WIDTH(4)
  ) add (
      .x(x),
      .y(x),
      .sum(sum)
  );
endmodule
