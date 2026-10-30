# CLAUDE.md

DigSim (`digsim-logic-simulator` on PyPI): digital logic simulator with a PySide6 GUI, a
Python API, and Yosys (`yowasp-yosys`) to synthesize Verilog. Python >= 3.11 (CI 3.11–3.15),
no newer-only syntax. Dependencies in `pyproject.toml` pinned exactly.

## Layout

- `src/digsim/circuit/`: simulation core, components in `components/`, ports in
  `components/atoms/`, IC netlists in `components/ic/`
- `src/digsim/app/`: GUI (`cli.py`, `gui/`, `gui_objects/`, `model/`, `settings/`)
- `src/digsim/synth/` Yosys synthesis, `storage_model/` pydantic save/load, `utils/` netlists
- `tests/`, `examples/` (pytest testbenches in `examples/pytest_tb/`), `circuits/` (a folder
  per GUI circuit with its files), `tools/gui_fuzz.py`, `docs/` (MkDocs Material, published
  to https://freand76.github.io/digsim/)

## Commands

Use `uv`. Ruff via `uv tool run`.

```sh
uv tool run ruff format && uv tool run ruff check   # --fix for autofixes
uv run --with pytest pytest      # tests/ and examples/pytest_tb/
uv run --with mypy mypy          # local only
uv run -m digsim.app             # GUI
uv tool run --with mkdocs-material --with mkdocstrings-python --with ruff mkdocs build --strict
uv run --with pytest python docs/scripts/generate_examples.py   # example images
uv run python docs/scripts/generate_tutorial.py                 # GUI tutorial screenshots
uv run python docs/scripts/generate_editor_image.py             # Verilog editor screenshot
uv run python docs/scripts/generate_gui_images.py   # component images, screenshots, icon
uv run python docs/scripts/generate_verilog_tutorial.py
uv run python docs/scripts/generate_new_verilog_tutorial.py
uv run python tools/gui_fuzz.py --seeds 3,11,21 --steps 300  # GUI test, offscreen
uv run --with pytest pytest tools/gui_editor_check.py         # Verilog GUI checks
```

- Ruff, mypy and pytest before committing. `uv run --with .` from another project can use
  a stale build (`--reinstall`).
- `/tmp` is not usable for circuits, Verilog or copies of them (nor a scratchpad under
  `/tmp`): Yosys can't read files there, the load fails and the GUI blocks on a warning
  dialog. Use a folder in `~/.cache`.

## CI

Runs on push: ruff, `full_scope.yaml` (all tests and `examples/yosys_counter/*.py`, Linux
x86_64, 3.11–3.15, native and Python engine), `minimal_scope.yaml` (Windows, Linux arm64,
macOS: `sanity` tests with both engines, `tools/native/`). `docs.yaml` deploys on pushes
to `main` touching `docs/`, `src/digsim/`, `mkdocs.yml`, `CHANGELOG.md`. Don't watch CI.

- Mark test files with platform-sensitive parts (files, paths, line endings, Yosys, the
  Verilog formatter, native engine) `pytestmark = pytest.mark.sanity`.
- Tests must not import `QtGui`/`QtWidgets` (no `libEGL` in CI): keep testable logic in
  Qt-free modules. The GUI has no CI tests: check by running the app
  (`QT_QPA_PLATFORM=offscreen` for scripts), `tools/gui_fuzz.py` (the `gui-tester` agent)
  and `tools/gui_editor_check.py`. Windows path/locking problems only show in Windows CI.

## Code conventions

- Header `# Copyright (c) Fredrik Andersson, 2023-2026` / `# All rights reserved`, then a
  module docstring. Editing a file sets the second year to the current year.
- Private modules `_name`, re-exported by the package `__init__.py`.
- Ruff config in `pyproject.toml`: line length 99, PySide6 own isort section, two blank
  lines after imports, no relative imports from parent packages.
- Fully typed (`disallow_untyped_defs`). Ports are typed via `Component.__getattr__`, GUI
  objects narrow their `component` property.
- Qt: fully qualified enums (`Qt.GlobalColor.red`), `int()` for int APIs.
- Google style docstrings on public API, components list ports under `Ports:`.
  `docs/api/` (mkdocstrings) lists the members to show: add new public API, not plumbing.

## Simulation core

- Changes to `circuit/` (events, ports, VCD) keep every example's output and VCD
  byte-identical, also the order of same-time events (Yosys gate designs race). Compare a
  `git archive` copy of `main` with the tree. `examples/yosys_6502` prints its run time.
- Events are `CircuitEvent` (a `float` subclass) on a heap; don't change the tie order. An
  event replaced by a later one for the same port is skipped.
- `Port` is hot: don't change class attributes of hot classes repeatedly at runtime.
- Values: int, "X" (undefined), "Z" (not driven). All ports "X" after `Circuit.init()`, an
  input is "X" again when its last driver is removed. Several drivers: `resolve()`
  replaces `set_value`.
- `Circuit.add_component` suffixes taken names. Parts of a component (SR latch gates,
  Yosys netlists) are in the circuit but not saved, see `change_component_name`.
- Storage and GUI create `cls(circuit, **settings)`, then set the name. `get_parameters()`
  defaults must match `__init__`. `YosysComponent`/`IntegratedCircuit` take the module name.
- Yosys runs in-process (`yowasp_yosys.run_yosys`), never native. YoWASP has its own
  `/tmp` and `/share` and doesn't follow absolute links: work files go in the user cache,
  `_yosys_path()` resolves links, paths use forward slashes. A failed run keeps files open
  until GC (breaks Windows cleanup).
- Check synthesis against Icarus (`iverilog`): random Verilog as gates and with
  `functional=True` must agree.

## Creating components

- Model: `circuit/components/_name.py`, a `Component` (or `CallbackComponent` to repaint
  the GUI via `super().update()`), exported in `components/__init__.py`. Store every
  `__init__` argument with `parameter_set`, describe them in `get_parameters()` (types in
  `Parameter`, `"reconfigurable": True` to change without rebuilding).
- Wiring ports calls `update()`: set up state before `add_port`. Reset state in
  `default_state()`. Edges: `port.is_rising_edge()` once per `update()`. Inout pins:
  `PortInOut` with a `PortOutDelta(delay_ns=0)` driver and a `PortIn` reader per bit (see
  `CircuitInOut`). A timer: an internal `PortOutDelta` with `update_parent(True)`.
- Test both engines (`DIGSIM_ENGINE=python`), in `tests/test_name.py`.
- GUI: `app/gui_objects/_name_object.py`, a `ComponentObject` with `paint_component`,
  `paint_selectable_component` (selector icon), `update_ports`/`port_direction` for custom
  port places. Register in `_gui_object_factory.py` and `app/_component_catalog.py`
  (`tests/test_component_catalog.py`), add to `COMPONENTS` in `tools/gui_fuzz.py`.
- Docs: a row in `docs/gui.md`, `docs/python.md`, `docs/api/components.md`, an image entry
  in `generate_gui_images.py`, and `CHANGELOG.md`. `docs/components.md` and
  `docs/gui-components.md` walk through `XNOR` and `LedBar`.
- Scripted circuit edits (offscreen `AppModel`): spin the event loop after loading, add
  new objects with `area.scene().add_scene_component()`, never emit
  `sig_synchronize_gui` yourself (it deletes the existing items).

## GUI

- Model signals come from the simulation thread (queued): GUI objects never connect to
  them, the circuit area forwards them.
- Reset, add, undo, redo and load call `model_init()`: time 0, VCD starts over.

## Docs

- `docs/documentation.md` only points to the site. No semicolons in prose (code exempt).
  Ruff formats Python blocks in Markdown (CI checks).
- `generate_gui_images.py` draws `docs/images/components/`, app screenshots,
  `docs/images/guide/` and the icon (`src/digsim/app/images/app_icon.png`, copy in
  `docs/images/`). Regenerate example images when an example changes.

## Commits and git

- One single-purpose commit per change. Messages say **why** (what was wrong or missing
  for the user), imperative subject, short body. **Never** a `Co-Authored-By` or other
  attribution line.
- Commit only when asked or the task asks (a plan: one commit per part). Push only when
  asked, ask before force push, never amend a pushed commit.
- Never commit untracked root files (`dist/`, `requirements.txt`, `uv.lock`,
  `test.circuit`, `plans/`). Never `git stash` (WIP stashes), test old code from a
  `git archive` copy.
- User-visible changes: a line in `## vx.x.x` at the top of `CHANGELOG.md`.

## Releases

1. Bump `version` in `pyproject.toml`, turn `## vx.x.x` into the version ("Prepare for
   release x.y.z" commit).
2. `bash create_dist_pkg.sh` builds `dist/` (and `requirements.txt` with pip-compile).
3. `twine upload dist/*` is **always the maintainer's**. Never upload anything.
