// A string macro, given to the synthesis by the tests: y is 1 if it is the expected text
module string_macro (
  output logic [1:0] y
);

  assign y = (`TEXT == "path/to/some (random quote)/a;b#c.wow") ? 2'd1 : 2'd2;

endmodule
