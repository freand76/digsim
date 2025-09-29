// Copyright (c) Fredrik Andersson, 2023-2025
// All rights reserved

module ic7448 (bcd, lt, a,b,c,d,e,f,g);
   input [3:0] bcd;
   input       lt;
   output      a;
   output      b;
   output      c;
   output      d;
   output      e;
   output      f;
   output      g;

   wire [6:0] seg;
   assign a = seg[6];
   assign b = seg[5];
   assign c = seg[4];
   assign d = seg[3];
   assign e = seg[2];
   assign f = seg[1];
   assign g = seg[0];

   always @(bcd or lt)
     begin
        if (lt)
          seg = 7'b1111111;
        else begin
          case (bcd)
            0 : seg = 7'b1111110;
            1 : seg = 7'b0110000;
            2 : seg = 7'b1101101;
            3 : seg = 7'b1111001;
            4 : seg = 7'b0110011;
            5 : seg = 7'b1011011;
            6 : seg = 7'b1011111;
            7 : seg = 7'b1110000;
            8 : seg = 7'b1111111;
            9 : seg = 7'b1111011;
            default : seg = 7'b0000000;
          endcase // case (bcd)
        end
     end
endmodule
