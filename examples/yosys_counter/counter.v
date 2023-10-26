module counter(clk, reset, up, long_counter);

   input clk, reset, up;

   output reg [3:0] long_counter;

   always @(posedge clk or posedge reset)
     begin
        long_counter <= long_counter;
        if (reset)
          long_counter <= 0;
        else
          if (up)
            long_counter <= long_counter + 1;
     end

endmodule
