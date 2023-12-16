module error_module(clk, reset, cnt);

   input clk, reset;

   output reg [3:0] xcnt;

   always @(posedge clk or posedge reset)
     begin
        cnt <= cnt;
        if (reset)
          cnt <= 0;
        else
          cnt <= cnt + 1;
     end

endmodule
