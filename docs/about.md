# About

DigSim is written by Fredrik Andersson. It is open source under the
[Clear BSD License](https://github.com/freand76/digsim/blob/main/LICENSE.md), and the code
is on [GitHub](https://github.com/freand76/digsim).

## History

DigSim started in December 2022 as a way to see simple Verilog modules in action: wire a
module to buttons, switches and LEDs, and play with it. A week after the first commit, a
4-bit counter synthesized by Yosys ran in the simulator, and the first release followed in
2023.

The core of DigSim was written by hand from the start: the event-driven simulation engine,
the components and ports, the import of Yosys netlists, and the first version of the GUI.
It has since grown to simulate larger designs, like the
[6502 CPU](https://en.wikipedia.org/wiki/MOS_Technology_6502), to synthesize Verilog
with a bundled WebAssembly Yosys, and to edit Verilog in the GUI.

## AI in the later stages

In the later stages of the project, AI has been used for hunting bugs, for new
development, and for refining what was there: the code, the tests, the GUI and these
docs.

## Feedback

Bug reports and ideas are welcome as
[issues on GitHub](https://github.com/freand76/digsim/issues). See
[Contributing](contributing.md) to help out.
