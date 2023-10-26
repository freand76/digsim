module counter(clk, reset, up, cnt);

   input clk, reset, up;

   output reg [3:0] cnt;

   always @(posedge clk or posedge reset)
     begin
        cnt <= cnt;
        if (reset)
          cnt <= 0;
        else
          if (up)
            cnt <= cnt + 1;
     end

endmodule
