// A traffic light: a state machine with its states as a SystemVerilog enum, so that the
// names of the states are in the Yosys netlist. A request turns the light from red to
// green, and back after a while.

module traffic_light (
    input  logic clk,
    input  logic reset,
    input  logic request,
    output logic red,
    output logic yellow,
    output logic green
);
   typedef enum logic [1:0] {
      RED = 2'd0,
      RED_YELLOW = 2'd1,
      GREEN = 2'd2,
      YELLOW = 2'd3
   } state_t;

   state_t state;
   // The clock cycles left in the state
   logic [2:0] timer;

   always_ff @(posedge clk) begin
      if (reset) begin
         state <= RED;
         timer <= 3'd0;
      end else if (timer != 3'd0) begin
         timer <= timer - 3'd1;
      end else begin
         case (state)
           RED:
             if (request) begin
                state <= RED_YELLOW;
                timer <= 3'd1;
             end
           RED_YELLOW: begin
              state <= GREEN;
              timer <= 3'd4;
           end
           GREEN: begin
              state <= YELLOW;
              timer <= 3'd1;
           end
           default: begin
              state <= RED;
              timer <= 3'd2;
           end
         endcase
      end
   end

   assign red = state == RED || state == RED_YELLOW;
   assign yellow = state == RED_YELLOW || state == YELLOW;
   assign green = state == GREEN;
endmodule
