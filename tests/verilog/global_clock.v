// A register on the implicit global clock, which DigSim can't simulate (tests/test_yosys_reload.py)
module global_clock (
    input d,
    output reg q
);
    always @($global_clock) q <= d;
endmodule
