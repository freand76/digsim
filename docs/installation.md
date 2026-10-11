# Installation

DigSim is published on PyPI as
[`digsim-logic-simulator`](https://pypi.org/project/digsim-logic-simulator/) and
requires **Python 3.10 or newer**. All dependencies, including the Qt GUI toolkit and the
Yosys synthesis tool, are installed automatically.

Pick the option that suits you:

| I want to... | Use |
| --- | --- |
| Try DigSim without installing anything permanently | [Run with uvx](#run-with-uvx-no-installation) |
| Have the `digsim-logic-simulator` command always available | [Install as a tool](#install-as-a-command-line-tool) |
| Use DigSim from my own Python scripts or tests | [Install into a virtual environment](#install-into-a-virtual-environment) |
| Run the examples or work on DigSim itself | [Run from source](#run-from-source) |

## Run with uvx (no installation)

[uv](https://docs.astral.sh/uv/) can download and run DigSim in a temporary, isolated
environment with a single command:

```sh
uvx digsim-logic-simulator
```

The first start takes a little while since packages are downloaded; later starts are
fast thanks to uv's cache. Add `@latest` to make sure you get the newest release:

```sh
uvx digsim-logic-simulator@latest
```

## Install as a command-line tool

Install DigSim once into its own isolated environment and get the
`digsim-logic-simulator` command on your `PATH`.

=== "uv"

    ```sh
    uv tool install digsim-logic-simulator
    digsim-logic-simulator
    ```

    Upgrade later with `uv tool upgrade digsim-logic-simulator`.

=== "pipx"

    ```sh
    pipx install digsim-logic-simulator
    digsim-logic-simulator
    ```

    Upgrade later with `pipx upgrade digsim-logic-simulator`.

## Install into a virtual environment

Use this when you want to `import digsim` in your own Python code, for example to
[script circuits](python.md) or write testbenches.

=== "uv"

    ```sh
    uv venv
    uv pip install digsim-logic-simulator
    ```

    Or, inside a uv-managed project: `uv add digsim-logic-simulator`.

=== "pip (Linux / macOS)"

    ```sh
    python3 -m venv .venv
    source .venv/bin/activate
    pip install digsim-logic-simulator
    ```

=== "pip (Windows)"

    ```powershell
    py -m venv .venv
    .venv\Scripts\activate
    pip install digsim-logic-simulator
    ```

Start the GUI from the activated environment with either of:

```sh
digsim-logic-simulator
python -m digsim.app
```

## Run from source

Clone the repository to get the [example circuits](https://github.com/freand76/digsim/tree/main/example_circuits),
the [Python examples](https://github.com/freand76/digsim/tree/main/examples), or to
contribute to DigSim.

```sh
git clone https://github.com/freand76/digsim.git
cd digsim
```

=== "uv"

    ```sh
    uv sync
    uv run -m digsim.app
    ```

    `uv sync` creates `.venv` and installs DigSim in editable mode, so code changes take
    effect without reinstalling. Prefix other commands with `uv run`, for example
    `uv run python examples/example_sr.py`.

=== "pip"

    ```sh
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    python -m digsim.app
    ```

## Command-line options

```text
digsim-logic-simulator [--load CIRCUIT] [--version]
```

| Option | Description |
| --- | --- |
| `--load`, `-l` | Load a saved circuit at startup, e.g. `--load example_circuits/counter_yosys_netlist.circuit` |
| `--version`, `-v` | Print the installed version and exit |

`python -m digsim.app` accepts the same options.

## Troubleshooting

### Linux: "Could not load the Qt platform plugin xcb"

If the application fails to start with:

```text
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized.
```

install the missing XCB cursor library. On Ubuntu and Debian:

```sh
sudo apt install libxcb-cursor0
```

### Viewing waveforms

DigSim writes waveforms as VCD files but has no built-in viewer. Install
[GTKWave](https://gtkwave.sourceforge.net/) (on Ubuntu: `sudo apt install gtkwave`) or
another VCD viewer such as [Surfer](https://surfer-project.org/).
