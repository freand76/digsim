module fibonacci(clk, reset, index, value);

   input clk, reset;

   output reg [15:0] index;
   output [15:0] value;

   reg [15:0]        first;
   reg [15:0]        next;
   wire [15:0]       sum;
             
   always_comb
     sum <= first + next;

   always_comb
     value <= first;

   always @(posedge clk or posedge reset)
     begin
        next <= sum;
        first <= next;
        index <= index + 1;  
        if (reset)
          begin
             index <= 0;
             first <= 0;
             next <= 1;
          end
     end

endmodule
