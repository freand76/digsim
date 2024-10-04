module up_down_counter(clk, nrst, up, down, value);

   input clk;
   input nrst;
   input up;
   input down;
   output reg [3:0] value;

   always @ (posedge clk, negedge nrst)
     begin
        if (nrst == 0)
          begin
             value <= 0;
          end
        else
          begin
             if (up)
               begin
                  value <= value + 1;
               end
             else if (down)
               begin
                  value <= value - 1;
               end
          end
     end

endmodule // up_down_counter
