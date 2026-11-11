// A register with a $display: the $print cell has inputs and no outputs, DigSim ignores it
// (tests/test_yosys_functional.py)
module display (
    input clk,
    input [7:0] d,
    output reg [7:0] q
);
    always @(posedge clk) begin
        q <= d;
        $display("d = %d", d);
    end
endmodule
