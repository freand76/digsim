# Contributing

Contributions to DigSim are welcome, big and small: bug reports, ideas, documentation,
examples, new components and fixes. DigSim is developed on
[GitHub](https://github.com/freand76/digsim).

## Reporting bugs and suggesting ideas

Open an [issue](https://github.com/freand76/digsim/issues). For a bug, please include:

- the DigSim version (`digsim-logic-simulator --version`), your operating system and
  Python version,
- what you did, what you expected and what happened instead, with the full error message,
- the circuit file or Python script that shows the problem, if you have one.

Ideas and questions are welcome as issues too.

## Development setup

DigSim uses [uv](https://docs.astral.sh/uv/) for development.

1. [Fork](https://github.com/freand76/digsim/fork) the repository on GitHub and clone
   your fork:

    ```sh
    git clone https://github.com/<your-user>/digsim.git
    cd digsim
    ```

2. Create the virtual environment, with DigSim installed in editable mode:

    ```sh
    uv sync
    ```

3. Start the application from the source tree, so your changes take effect directly:

    ```sh
    uv run -m digsim.app
    ```

### Where things are

| Path | Contents |
| --- | --- |
| `src/digsim/circuit/` | The simulator: `Circuit`, components and ports (`components/atoms/`) |
| `src/digsim/app/` | The GUI application: main window (`gui/`), component drawing (`gui_objects/`), model and settings dialogs |
| `src/digsim/synth/`, `src/digsim/utils/` | Yosys synthesis and netlist parsing |
| `src/digsim/storage_model/` | The file format for saved circuits |
| `tests/` | The tests |
| `examples/`, `circuits/` | Python examples and GUI circuits, see [Python Examples](python-examples.md) and [GUI Examples](gui-examples.md) |
| `docs/` | This documentation |

To add a component, follow [Creating Components](components.md) and
[Adding Components to the GUI](gui-components.md).

## Before you submit

Run the same checks as the continuous integration, from the repository root:

```sh
uv tool run ruff format                        # format the code
uv tool run ruff check                         # lint
uv run --with mypy mypy                        # type check
uv run --with pytest pytest                    # run the tests
```

The tests run on Linux with Python 3.11 to 3.15 and on Windows, so avoid syntax newer than
Python 3.11.

For documentation changes, preview the site while you edit it, at <http://127.0.0.1:8000/digsim/>:

```sh
uv tool run --with mkdocs-material --with mkdocstrings-python --with ruff mkdocs serve
```

If you change an example, regenerate the images on the [Python Examples](python-examples.md)
and [GUI Examples](gui-examples.md) pages:

```sh
uv run --with pytest python docs/scripts/generate_examples.py
```

If you change how the GUI looks or works, regenerate the screenshots in
[Your First Circuit](first-circuit.md):

```sh
uv run python docs/scripts/generate_tutorial.py
```

and the component images of the [GUI Reference](gui.md), the screenshots of the
application, the images of [Adding Components to the GUI](gui-components.md) and the
application icon:

```sh
uv run python docs/scripts/generate_gui_images.py
```

The screenshots of the Verilog guides,
[Your First Verilog Component](new-verilog.md) and
[Editing a Verilog Component](verilog-tutorial.md), and of the Verilog editor in the
[GUI Reference](gui.md#the-verilog-editor):

```sh
uv run python docs/scripts/generate_new_verilog_tutorial.py
uv run python docs/scripts/generate_verilog_tutorial.py
uv run python docs/scripts/generate_editor_image.py
```

## Guidelines

- **Keep changes focused.** One fix or feature per pull request, and one purpose per
  commit, makes changes easy to review.
- **Explain why.** Commit messages and pull request descriptions should say what was wrong
  or missing, not only what the code does.
- **Add tests** for new components and bug fixes in `tests/`.
- **Annotate types.** All functions have type annotations, and mypy rejects functions
  without them.
- **Use full Qt enum names**, such as `Qt.GlobalColor.red` instead of `Qt.red`.
- **Update the documentation** when you change behavior, and add a line to the top
  section of `CHANGELOG.md` for user-visible changes.

## Submitting a pull request

1. Create a branch in your fork for the change: `git switch -c my-change`.
2. Commit your changes and push the branch to your fork.
3. Open a [pull request](https://github.com/freand76/digsim/pulls) against the `main`
   branch, describing what the change does and why.
4. The Ruff check runs on the pull request. The tests run when you push to a repository
   with GitHub Actions enabled, so enable Actions in your fork to see them before you open
   the pull request.

DigSim is licensed under the
[Clear BSD License](https://github.com/freand76/digsim/blob/main/LICENSE.md), and your
contributions are licensed under the same terms.
