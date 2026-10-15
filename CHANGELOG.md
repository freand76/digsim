# CHANGELOG

## vx.x.x
 - Add a script that takes the screenshots for a GUI tutorial in the real application
 - Add "Your First Circuit", a step by step guide with screenshots to building and simulating a circuit in the GUI, and group the GUI pages in the documentation
 - Bugfix: Circuits saved on Windows stored file paths with backslashes and could not be loaded on Linux or macOS. Paths are now stored with "/", and old files with backslashes load on all systems.
 - Circuit.to_json_file() stores file paths relative to the JSON file, and from_json_file() reads them from the file's folder by default, so a saved circuit loads from any working directory. Files saved by older versions with such paths load with folder=".".
 - More tests for how Yosys components are wired from a netlist
 - The Yosys netlist model only reads the parts of a netlist that DigSim uses. Net names, attributes and cell parameters are no longer stored.
 - Simpler Yosys netlist nets: NetPort names its cell (None for a module port) instead of holding the cell or module object, and loading the 6502 netlist is about 30% faster
 - Yosys components no longer add an empty "nets" component to the circuit, and the unused nets argument is removed
 - Bugfix: A Verilog module with an input that it does not use, or a netlist with an unused cell output, could not be loaded
 - Simpler Yosys component code
 - Bugfix: A GUI object that subclasses another image object with its own image showed the base class image
 - Correct the descriptions of several GUI object classes
 - Remove unused and repeated code from the GUI objects
 - Simpler port handling in the GUI objects
 - GUI objects choose whether to show the component name and port names with the SHOW_NAME and SHOW_PORT_NAMES class attributes, described in the guide for adding components
 - NamedBoxObject: a base class for GUI objects drawn as a box with their name, like ICs, described in the guide for adding components
 - Simpler label wire GUI objects, which no longer choose their shape by looking for "in" in a text
 - The DIP switch only repaints the circuit when the mouse moves to another switch, not on every mouse move
 - The DIP switch GUI object draws itself in paint_component(), like the other GUI objects
 - The guide for adding components says that mypy reports a GUI object without paint_component() or paint_selectable_component()
 - Bugfix: Ctrl+Z, Ctrl+Y and Del changed the circuit while the simulation was running
 - Bugfix: Wires could be selected while the simulation was running
 - Bugfix: The Delete button stayed disabled after selecting a component or wire
 - Fix the grammar of the question before a circuit is replaced, and add the missing Zoom in tooltip
 - Remove unused code and correct docstrings in the main window, circuit area, top bar and component selector
 - Simpler mouse wheel zoom code
 - The component selector and circuit area are placed side by side without a splitter, which showed a grip that could not be dragged
 - Bugfix: Settings on a Static Value component showed "Unknown settings type" instead of the value slider
 - Bugfix: A new Note placed without editing its text was empty instead of showing the default text
 - Bugfix: An update frequency from a circuit file that is not in the settings list was lost when the settings were saved, and the next simulation start failed
 - Simpler component settings dialog code
 - The default application settings are kept in the model instead of the settings dialog
 - Bugfix: Pressing Del with nothing selected added an undo step that did nothing
 - Bugfix: Bring to front and Send to back could not be undone on their own
 - Bugfix: A circuit file with an update frequency of 0 or an unknown setting value made the simulation fail to start. Such settings are now ignored.
 - Remove unused code and correct docstrings in the application model
 - Bugfix: For a moment after a single step, the GUI treated the simulation as stopped while its thread still used the circuit, so it could be changed under it
 - Bugfix: A circuit file that is valid JSON but not an object (like a list) raised TypeError instead of being reported as malformed
 - Bugfix: Loading a folder or a file without read permission raised an exception instead of showing an error
 - Bugfix: A circuit file with an unknown component type, or a setting that a component does not have, stopped the whole load instead of giving a warning for that component. Types that are not components are refused.
 - Bugfix: Components from circuit files without display names got an empty name in the GUI
 - Bugfix: A circuit with a dot in a component name could be saved but not loaded
 - Simpler storage model code
 - Bugfix: A synthesis whose console file could not be opened left two file descriptors open
 - Bugfix: python -m digsim.synth ended with a traceback when the output file could not be written, and printed "ERROR:" twice
 - Bugfix: The error for reading a component's wire showed a method instead of the component name. The unused Component.settings_from_dict() is removed.
 - Bugfix: Changing several settings of a component reconfigured it once per setting, partly with the old settings
 - Port.disconnect() only disconnects a port that it drives, a wrong call no longer cuts another connection

## v1.3.0
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
 - Bugfix: A VCD file that could not be opened left the circuit unable to run or start another VCD
 - Bugfix: Choosing a VCD file that cannot be written raised an exception instead of showing an error
 - Bugfix: Saving to a folder that cannot be written raised an exception instead of showing an error
 - Components built from other components no longer initialize their parts a second time. This only changes the first nanoseconds of the VCD files of Yosys designs.
 - Remove the unused Port.width setter, which did not resize the bits of a bus port
 - The IC selector lists the ICs sorted by name
 - Bugfix: The buzzer clicked once a second for all tones except A
 - Bugfix: Label wires were shared by all circuits in a program, so two circuits could not use the same label. The labels in use are now read with Component.get_circuit_parameters(circuit).
 - Bugfix: Deleting a label wire driver in the GUI made the next reset or start fail
 - Label wires are shown while they are dragged into the circuit area, with the label they get when dropped
 - Bugfix: A button press or release just before the simulation stopped was handled at the next start, also after a reset
 - Bugfix: Saving a Yosys component created from a netlist object stored the path "None". It now gives an error.
 - Bugfix: A new component could take over the shortcut key of a deleted component with the same name
 - A label wire output without a matching label wire input gives a warning when the circuit is initialized
 - Keep at most 100 undo steps, so memory use does not grow during a long session
 - Yosys gate cells propagate undefined inputs ("X") as in Verilog, instead of treating them as 0. The simulation results are the same, but VCD files show X until a design has settled after the start.
 - The Fibonacci synthesis example starts with clock and reset low, so they are not undefined at the start of its waveforms
 - Drop support for Python 3.10, which has reached its end of life. DigSim requires Python 3.11 or newer.
 - Simpler documentation image script, using contextlib.chdir from Python 3.11

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
