// Combinational operations, synthesized into gates and into functional cells in
// tests/test_yosys_functional.py, which compares the two

module functional_comb (
    input [3:0] a,
    input [3:0] b,
    input signed [3:0] sa,
    input signed [3:0] sb,
    input [1:0] s,
    output [4:0] y_add,
    output [3:0] y_sub,
    output [7:0] y_mul,
    output [3:0] y_div,
    output [3:0] y_mod,
    output signed [3:0] y_sdiv,
    output signed [3:0] y_smod,
    output signed [4:0] y_neg,
    output [5:0] y_cmp,
    output [1:0] y_scmp,
    output [3:0] y_shl,
    output [3:0] y_shr,
    output signed [3:0] y_sshr,
    output [1:0] y_part,
    output [2:0] y_logic,
    output [3:0] y_reduce,
    output [3:0] y_and,
    output [3:0] y_or,
    output [3:0] y_xor,
    output [3:0] y_xnor,
    output [3:0] y_not,
    output [3:0] y_mux,
    output reg [3:0] y_case,
    output [2:0] y_decode
);
   // No division by zero: that is undefined in the functional cells
   wire [3:0] b_nonzero = b | 4'b0001;
   wire signed [3:0] sb_nonzero = sb | 4'sb0001;

   assign y_add = a + b;
   assign y_sub = a - b;
   assign y_mul = a * b;
   assign y_div = a / b_nonzero;
   assign y_mod = a % b_nonzero;
   assign y_sdiv = sa / sb_nonzero;
   assign y_smod = sa % sb_nonzero;
   assign y_neg = -sa;
   assign y_cmp = {a < b, a <= b, a > b, a >= b, a == b, a != b};
   assign y_scmp = {sa < sb, sa >= sb};
   assign y_shl = a << b[1:0];
   assign y_shr = a >> b[1:0];
   assign y_sshr = sa >>> b[1:0];
   wire [7:0] ab = {a, b};
   assign y_part = ab[s * 2 +: 2];
   assign y_logic = {a && b, a || b, !a};
   assign y_reduce = {&a, |a, ^a, ~^a};
   assign y_and = a & b;
   assign y_or = a | b;
   assign y_xor = a ^ b;
   assign y_xnor = a ~^ b;
   assign y_not = ~a;
   assign y_mux = s[0] ? a : b;

   always @* begin
      case (s)
        2'd0: y_case = a;
        2'd1: y_case = b;
        2'd2: y_case = a & b;
        default: y_case = a | b;
      endcase
   end

   // Comparisons of the same input with constants, simulated as one decoder
   assign y_decode = {a == 4'd3, a == 4'd9, a != 4'd12};
endmodule
