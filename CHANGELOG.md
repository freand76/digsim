# CHANGELOG

## vx.x.x
 - Use pydantic to load yosys netlist

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
