# CHANGELOG

## vx.x.x

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
