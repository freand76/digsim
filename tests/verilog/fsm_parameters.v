// A state machine with its states as parameters, for the state names of Yosys components.
// 'other' has the width of the states too, 'flag' has one bit like the ONE parameter,
// and 'state_name' has the name that the names of 'state' would get.

module fsm_parameters (
    input clk,
    input reset,
    output done,
    output [7:0] internal
);
    parameter IDLE = 2'd0;
    parameter RUN = 2'd1;
    parameter DONE = 2'd2;
    parameter ONE = 1'b1;

    reg [1:0] state;
    reg [1:0] other;
    reg flag;
    reg [3:0] state_name;

    always @(posedge clk) begin
        if (reset) begin
            state <= IDLE;
            other <= 2'd0;
            flag <= 1'b0;
            state_name <= 4'd0;
        end else begin
            other <= other + 2'd1;
            flag <= ~flag;
            state_name <= state_name + 4'd1;
            case (state)
                IDLE: state <= RUN;
                RUN: state <= DONE;
                default: state <= DONE;
            endcase
        end
    end

    assign done = state == DONE;
    // Not optimized away
    assign internal = {other, flag, state_name[3:0], 1'b0};
endmodule
