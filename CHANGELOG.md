# CHANGELOG

## vx.x.x
 - Bugfix: Error and close dialogs were not attached to the main window
 - Use the Qt 6 mouse event API (no DeprecationWarning from QMouseEvent.pos())
 - Dragging from the component selector starts when the mouse moves, not on every click
 - Use the Qt 6 exec() instead of the Qt 5 exec_() for dialogs, menus and drags
 - Painting components no longer changes pens shared by all components of a type
 - Add the changelog to the documentation site
 - Simpler sentences in the documentation
 - Bugfix: Deleting a component left the components it is built from in the circuit
 - Circuit can be used in a with statement, which closes its VCD file at the end
 - Bugfix: Reloading a Yosys component kept its old gates in the circuit
 - Bugfix: The SR latch outputs Q and nQ were treated as inputs
 - Bugfix: The JK flip-flop toggled when K was undefined
 - Bugfix: Initializing a circuit again did not reset the T flip-flop output
 - Bugfix: The logic analyzer could draw a signal one sample short
 - Simpler on/off switch code, which no longer sets its output twice at init
 - Bugfix: HexDigit.dot_active() without a digit failed for a single digit
 - Bugfix: A label wire with a label already in use was left in the circuit
 - Simpler label wire code
 - Bugfix: MemStdOut printed characters while its write enable was undefined
 - Bugfix: A component that failed to load was left in the circuit
 - Simpler Yosys component code
 - Bugfix: Yosys flip-flops could miss the first clock edge after the circuit was reset
 - Fix a typo in the error message for an unknown Yosys cell level
 - Bugfix: Loading a circuit changed the stored component paths, so a second load failed
 - Bugfix: Synthesis failed for Verilog files in a folder with a space in its name
 - Simpler Yosys netlist code
 - Bugfix: Shortcut keys stopped working after undo, and a shortcut to a missing component stopped the circuit from loading
 - Bugfix: Loading a missing or broken circuit file crashed the application instead of showing an error
 - Bugfix: A buzzer kept its old tone after the tone was changed in its settings
 - Bugfix: A broken Yosys JSON netlist stopped a circuit from loading instead of giving a warning
 - Bugfix: Reloading a Yosys component whose file was moved raised an exception instead of a warning
 - Circuit.adding_components() removes the components a failing block added
 - Bugfix: A dropped component that failed to build, like a Verilog file with errors, raised an exception and left parts of it in the circuit
 - Bugfix: Turning VCD output off and on again in the GUI did not write the VCD file anymore

## v1.2.0
 - Update pyside6 to 6.12.0
 - Add Application icon for Wayland
 - Publish documentation at https://freand76.github.io/digsim/
 - Rewrite README and documentation with separate install/run options
 - Bugfix: Circuit.from_json_file() no longer requires a folder argument
 - Add type annotations to the whole package (checked with mypy)
 - Bugfix: Crash on init for Yosys async-load flip-flops with enable (_ALDFFE_*)
 - Bugfix: Crash instead of error dialog when a loaded circuit cannot be built
 - Bugfix: Synthesis crashed when given a pathlib.Path
 - Bugfix: Wire Source/Sink (label wires) lost their connections
 - Bugfix: Desktop menu entry started nothing and pointed at a stale interpreter
 - Fix "Similation" typo on the simulation start/stop button
 - Document all examples with circuit diagrams, expected output and waveforms
 - Add guides for creating components and for contributing
 - Add XNOR gate (2 to 8 inputs)
 - Add LED bar component, a row of LEDs showing the bits of a bus
 - Faster VCD output (2.3x faster simulation of the 6502 example with VCD)
 - Faster simulation (1.8x on the 6502 example)
 - 6502 example: VCD output is optional, enabled with --vcd [FILE]
 - Run Yosys in-process instead of through an interactive terminal (pexpect), about 3x faster synthesis
 - Bugfix: Crash when loading or changing a circuit right after stopping a simulation
 - Bugfix: Dropped components land centered under the mouse pointer
 - Show a preview of the component while dragging it into the circuit area
 - Silence harmless Qt Wayland text-input warnings in the terminal
 - Running from source with `uvx .` always uses the current code
 - Bugfix: Garbled package description on PyPI

## v1.1.0
 - Update python packages
 - Fix ruffing in code
 - Fixed windows test github action

## v1.0.0
 - Bugfix: Fix bad signal path
 - Bugfix: Disconnect signal before GUI component removal
 - Cleanup path handling

## v0.22.0
 - Remove dependency to pkg_resources (due to deprecation)

## v0.21.0
 - Add requirement to setuptools (for pkg_resources)

## v0.20.0
 - Add current version in window title bar
 - Bugfix documentation

## v0.19.0
 - Fix problems with script

## v0.18.0
 - Add executable 'digsim-logic-simulator'

## v0.17.0
 - Update uv test scripts
   - Clear venv before creating it
   - Use python 3.13
 - Add uv_ruff.sh script
 - Use "uv sync" instead of "uv pip install ."
 - Add python 3.14 support to project
 - Run pytest with python 3.14 (uv_run_test.sh)
 - Update to yosys 0.60.0

## v0.16.0
 - Update pyside6 package to 6.10.0
 - Update uv test scripts
 - Update to yosys 0.59.0 (And update yosys netlist reader)

## v0.15.0
 - Avoid creating new wires when simulation is running
 - Start/Stop simulation with space key
 - Abort ongoing new wire when simulation starts

## v0.14.0
 - Drop python 3.9 support
 - Remove abc from yosys synthesize script
 - Update pydantic and yowasp-yosys packages

## v0.13.0
 - Fix validation "0", "1", "X" in yosys netlist
 - Fix value type in _port.py (int, "X" or None is valid)
 - Remove None from value type in _port.py (int, "X" is now valid)
 - Optimize simulation with the help of Gemeni
 - Use pathlib everywhere (and not os.path)
 - Optimize event handling (suggestion from Gemini)

## v0.12.0
 - Use default audio output
 - Automatically find yowasp-yosys.exe binary on windows
 - Use pathlib for examples and test
 - Enable github/action for testing of python3.13 in windows

## v0.11.0
 - Fix settings load bug

## v0.10.0
 - Fix reload bug: Adding/removing port
 - Fix shortcuts load bug

## v0.9.0
 - Use pydantic to load yosys netlist
 - Update ruff github action
 - Update to yosys 0.57.0

## v0.8.0
 - Prepare for release 0.8.0
 - Bugfix netlist readed after yosys update
 - Update python packages
 - Some more mypy checking
 - Add types to _port.py file
 - Fixed some mypy checking
 - Update pyproject.toml to silence warnings
 - Update bash script to use latest version of pypi packages

## v0.7.0
 - Upgrade pypi packages and prepare for release 0.7.0
 - Add script to run pytest through uv
 - Use uv for scripts
 - Add python 3.13 to project
 - Use ruff 0.9.7 to format files
 - Update the python packages to "latest"
 - Fix version in changelog

## v0.6.0
 - Block bad pyside version 6.8.0

## v0.5.0
 - Added pytest verilog testbench example
 - Update python dependencies (yosys/pydantic/pyside6/...)
 - Update to ruff 0.6.9 (And fix code that ruff thought was bad)
 - Drop python 3.8 support

## v0.4.0
 - Make it possible to use locally installed yosys
 - Use ruff for python formatting and linting of code
 - Fix issue #3 (AttributeError when trying to delete objects)

## v0.3.1
 - Fix path in examples to work with github action

## v0.3.0
 - Use relative path in examples (for windows / yosys)
 - Use alternative pexpect spawn function in windows

## v0.2.0
 - Use yowasp-yoysys for synthesis

## v0.1.0
 * Fix bug when detecting number of modules with yosys 0.9
 * Improve error handling for yosys component
 * Remove settings from pushbutton and switch

## v0.0.1 - First Release
 * Simulation of a digital circuit using a python
 * Simulation of a yosys netlist using a python
 * GUI application to build and simulate circuit
