module demodesign(
                  clk, reset, in2, in3, in4, in5, in6, in7,
                  A, B, C, D, E, F, G, out7
);

   input clk, reset, in2, in3, in4, in5, in6, in7;
   output A, B, C, D, E, F, G, out7;

   reg [5:0] shift_register;
             
   always @(posedge clk or posedge reset)
     begin
        if (reset)
          shift_register[5:0] <= 1;
        else
          shift_register[5:0] <= {shift_register[4:0], shift_register[5]};
     end

   assign A = shift_register[0];
   assign B = shift_register[1];
   assign C = shift_register[2];
   assign D = shift_register[3];
   assign E = shift_register[4];
   assign F = shift_register[5];
              
endmodule
