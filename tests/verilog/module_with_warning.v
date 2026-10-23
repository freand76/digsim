// A module that synthesizes with warnings: b is not declared, and y2 is not driven

module warning_module(input a, output y, output y2);
   assign y = b;
endmodule
