// Flip-flops and a latch, synthesized into gates and into functional cells in
// tests/test_yosys_functional.py, which compares the two

module functional_regs (
    input clk,
    input rst_n,
    input en,
    input srst,
    input [3:0] d,
    output reg [3:0] q_dff,
    output reg [3:0] q_dffe,
    output reg [3:0] q_adff,
    output reg [3:0] q_adffe,
    output reg [3:0] q_sdff,
    output reg [3:0] q_sdffe,
    output reg [3:0] q_sdffce,
    output reg [3:0] q_latch
);
   always @(posedge clk) q_dff <= d;

   always @(posedge clk) if (en) q_dffe <= d;

   always @(posedge clk or negedge rst_n)
     if (!rst_n) q_adff <= 4'h5;
     else q_adff <= d;

   always @(posedge clk or negedge rst_n)
     if (!rst_n) q_adffe <= 4'ha;
     else if (en) q_adffe <= d;

   always @(posedge clk)
     if (srst) q_sdff <= 4'h3;
     else q_sdff <= d;

   always @(posedge clk)
     if (srst) q_sdffe <= 4'h6;
     else if (en) q_sdffe <= d;

   always @(posedge clk)
     if (en) begin
        if (srst) q_sdffce <= 4'hc;
        else q_sdffce <= d;
     end

   always @* if (en) q_latch = d;
endmodule
