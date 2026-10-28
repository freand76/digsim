# CLAUDE.md

DigSim (`digsim-logic-simulator` on PyPI): an interactive digital logic simulator with a
PySide6 GUI, a Python simulation API, and Yosys (via `yowasp-yosys`) for synthesizing
Verilog into simulatable netlists. Python >= 3.11 (CI tests 3.11–3.15), so no newer-only
syntax. Dependencies in `pyproject.toml` are pinned to exact versions.

## Layout

- `src/digsim/circuit/`: simulation core (`Circuit`, components in `components/`, ports and
  atoms in `components/atoms/`, bundled IC netlists in `components/ic/`)
- `src/digsim/app/`: GUI (`cli.py` entry point, `gui/`, `gui_objects/`, `model/`, `settings/`)
- `src/digsim/synth/`: Yosys synthesis (`python -m digsim.synth`)
- `src/digsim/storage_model/`: pydantic models for saving and loading circuits
- `src/digsim/utils/`: Yosys netlist parsing
- `tests/`, `examples/` (runnable, with pytest testbenches in `examples/pytest_tb/`),
  `example_circuits/` (GUI circuits), `tools/gui_fuzz.py` (randomized GUI test)
- `docs/`: MkDocs Material site (`mkdocs.yml`), published to https://freand76.github.io/digsim/

## Commands

Use `uv` for everything. Ruff runs via `uv tool run`, not as a project dependency.

```sh
uv tool run ruff format && uv tool run ruff check   # format, lint (--fix for autofixes)
uv run --with pytest pytest      # all tests (tests/ and examples/pytest_tb/)
uv run --with mypy mypy          # type check, local only
uv run -m digsim.app             # start the GUI
uv tool run --with mkdocs-material --with mkdocstrings-python --with ruff mkdocs build --strict
uv run --with pytest python docs/scripts/generate_examples.py  # regenerate example images
uv run python docs/scripts/generate_tutorial.py  # regenerate GUI tutorial screenshots
uv run python docs/scripts/generate_editor_image.py  # regenerate the Verilog editor screenshot
uv run python docs/scripts/generate_gui_images.py  # regenerate component images, app screenshots, icon
uv run python docs/scripts/generate_verilog_tutorial.py  # regenerate Verilog tutorial screenshots
uv run python docs/scripts/generate_new_verilog_tutorial.py  # regenerate new Verilog component guide screenshots
uv run python tools/gui_fuzz.py --seeds 3,11,21 --steps 300  # GUI test, offscreen
uv run --with pytest pytest tools/gui_editor_check.py  # Verilog GUI checks, offscreen
```

Run ruff format and check, mypy and pytest before committing. `uv run` rebuilds the
package, but `uv run --with .` from another project can use a stale build (`--reinstall`).

## CI

`.github/workflows/` runs ruff, and pytest plus `examples/yosys_counter/*.py`, on Linux
(3.11–3.15) and Windows, on push only. `docs.yaml` deploys the site on pushes to `main`
that touch `docs/`, `src/digsim/`, `mkdocs.yml` or `CHANGELOG.md`. Don't watch CI after
a push, the maintainer reports failures.

- CI can't load Qt's GUI libraries (no `libEGL`): tests must not import `QtGui` or
  `QtWidgets`. Keep testable logic in Qt-free modules (like `app/_desktop_entry.py`).
- The GUI has no tests in CI. `tools/gui_editor_check.py` has offscreen pytest checks of
  the Verilog editor and Reload, run it by hand. Check GUI changes by running the app
  (`QT_QPA_PLATFORM=offscreen` for scripts) and with `tools/gui_fuzz.py`, which edits
  circuits with random mouse actions and checks the GUI against the circuit after each
  step. The `gui-tester` agent (`.claude/agents/`) runs it.
- Things like Windows path and file locking problems only show up in the Windows CI.

## Code conventions

- Each source file starts with `# Copyright (c) Fredrik Andersson, 2023-2026` /
  `# All rights reserved`, then a module docstring. When you edit a file, make the second
  year of its header the current year.
- Private modules are prefixed `_` and re-exported through the package `__init__.py`.
- Ruff (config in `pyproject.toml`): line length 99, isort with PySide6 in its own
  section, two blank lines after imports, no relative imports from parent packages.
- Everything is type annotated (mypy `disallow_untyped_defs`). Component ports are added
  at runtime and typed via `Component.__getattr__`. GUI objects narrow their `component`
  property to the concrete type.
- Fully qualified Qt enums (`Qt.GlobalColor.red`), and `int()` for Qt APIs that take ints.
- Public classes and methods have Google style docstrings, and components list their
  ports under `Ports:`. The API Reference (`docs/api/`) is generated from them with
  mkdocstrings and lists the members to show: add new public API there, leave out
  internal plumbing that is only public by name.

## Simulation core

- Changes to `circuit/` (events, ports, VCD) must keep every example's output and VCD files
  byte-identical, including the order of events at the same time: Yosys gate-level designs
  have races where that order is visible. Compare a `git archive` copy of `main` with the
  changed tree by running each example in both and diffing their output and VCD files.
  `examples/yosys_6502` prints its run time, so that line always differs.
- Events are `CircuitEvent`, a `float` subclass (the time) on a heap, so comparisons run in
  C. The tie order must not change. An event that a later one for the same port replaced
  is skipped.
- `Port` is hot: don't change class attributes of hot classes repeatedly at runtime, after
  enough changes CPython stops optimizing attribute access on that class.
- Values are an int, "X" (undefined) or "Z" (not driven). Every port is "X" after
  `Circuit.init()`, and an input is "X" again when its last driver is removed. An input
  with several drivers gets its value from `resolve()`: its `set_value` is replaced while
  it has more than one.
- `Circuit.add_component` adds a suffix when a name is taken. Parts of a component (the
  gates of an SR latch or a Yosys netlist) are in the circuit too but not saved, so on
  load a part can hold the saved name of a component: `change_component_name` handles it.
- Storage and the GUI create components as `cls(circuit, **settings)` and set the name
  afterwards. The defaults in `get_parameters()` (GUI) must match the `__init__` defaults
  (Python). `YosysComponent` and `IntegratedCircuit` take the Verilog module's name.
- Yosys always runs in-process (`yowasp_yosys.run_yosys`, WebAssembly), never a native
  `yosys`. YoWASP mounts its own `/tmp` and `/share` and doesn't follow absolute links,
  so Yosys can't read files in `/tmp` (or pytest's `tmp_path` on Linux): work files go
  in a temp folder in the user cache. `_yosys_path()` gives Yosys the real path of a
  path with links, and reports the files it can't read. Paths given to Yosys use
  forward slashes (`C:/...`). After a failed run Yosys keeps its files open until
  garbage collection, which breaks cleanup on Windows.
- Synthesis changes can be checked against Icarus Verilog (`iverilog`, if installed): random
  Verilog synthesized as gates and with `functional=True` must agree with it.

## GUI

- The model's signals are emitted from the simulation thread, so they are queued. GUI
  objects must not connect to model signals themselves (a queued call to a removed object
  runs on freed memory). The circuit area receives them and forwards them.
- Reset, adding a component, undo, redo and loading call `model_init()`, which restarts
  the simulation at time 0 and starts the VCD file over.

## Docs

- `docs/documentation.md` only points to the site.
- Prose doesn't use semicolons unless one is really called for. Code examples are exempt.
- Ruff also formats Python code blocks in Markdown, and CI checks that.
- `docs/images/components/`, the app screenshots, `docs/images/guide/` and the app icon
  (`src/digsim/app/images/app_icon.png` and its copy `docs/images/app_icon.png`) are
  drawn by `docs/scripts/generate_gui_images.py`.
- `docs/components.md` (Python) and `docs/gui-components.md` (GUI) walk through the real
  `XNOR` and `LedBar` code, keep them in sync. Regenerate the example images when an
  example changes.

## Commits and git

- One commit per single-purpose change, don't bundle unrelated fixes.
- Messages are tight and say **why**: what was wrong or missing for the user, not how the
  code changes. Imperative subject, short body.
- **Never** add a `Co-Authored-By` trailer or any other attribution line.
- Commit only when asked or when the task asks for commits. When working through a plan
  with several parts, commit each part when it is done, one commit per feature. Push only
  when asked, ask before a force push, and don't amend a pushed commit (a follow-up is a
  new commit).
- Never commit the untracked files in the root (`dist/`, `requirements.txt`, `uv.lock`,
  `test.circuit`, `plans/`).
- Never use `git stash`: the maintainer keeps WIP stashes. To test old code, use a
  `git archive` copy.
- Add user-visible changes as a line in the `## vx.x.x` section at the top of
  `CHANGELOG.md`.

## Releases

1. Bump `version` in `pyproject.toml` and turn `## vx.x.x` in `CHANGELOG.md` into the new
   version ("Prepare for release x.y.z" commit).
2. `bash create_dist_pkg.sh` builds sdist and wheel into `dist/` (and regenerates
   `requirements.txt` with pip-compile).
3. `twine upload dist/*` is **always done by the maintainer**. Never run twine or upload
   anything.
