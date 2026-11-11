// Registers with and without initial values, and a RAM with initial contents
// (tests/test_yosys_init.py)
module initial_values (
    input clk,
    input we,
    input [1:0] addr,
    input [7:0] din,
    output [7:0] inited,
    output [3:0] partial,
    output [7:0] plain,
    output reg [7:0] ram_out
);
    reg [7:0] r_inited = 8'hA5;
    reg [3:0] r_partial = 4'b10xx;
    reg [7:0] r_plain;
    reg [7:0] ram [0:3];
    initial begin
        ram[0] = 8'h11;
        ram[1] = 8'h22;
        ram[2] = 8'h33;
        ram[3] = 8'h44;
    end
    always @(posedge clk) begin
        if (we) begin
            r_inited <= din;
            r_partial <= din[3:0];
            r_plain <= din;
            ram[addr] <= din;
        end
        ram_out <= ram[addr];
    end
    assign inited = r_inited;
    assign partial = r_partial;
    assign plain = r_plain;
endmodule
