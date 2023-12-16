module multi_module_one(clk, reset, cnt);

   input clk, reset;

   output reg [3:0] cnt;

   always @(posedge clk or posedge reset)
     begin
        cnt <= cnt;
        if (reset)
          cnt <= 0;
        else
          cnt <= cnt + 1;
     end

endmodule

module multi_module_two(clk, reset, cnt);

   input clk, reset;

   output reg [3:0] cnt;

   always @(posedge clk or posedge reset)
     begin
        cnt <= cnt;
        if (reset)
          cnt <= 0;
        else
          cnt <= cnt + 1;
     end

endmodule


module multi_module_three(clk, reset, cnt);

   input clk, reset;

   output reg [3:0] cnt;

   always @(posedge clk or posedge reset)
     begin
        cnt <= cnt;
        if (reset)
          cnt <= 0;
        else
          cnt <= cnt + 1;
     end

endmodule
