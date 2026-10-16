# CLAUDE.md

## Project

DigSim (`digsim-logic-simulator` on PyPI): an interactive digital logic simulator with a
PySide6 GUI, a Python simulation API, and Yosys (via `yowasp-yosys`) for synthesizing
Verilog into simulatable netlists.

- `src/digsim/circuit/` — simulation core (`Circuit`, components in `components/`,
  low-level ports/atoms in `components/atoms/`, bundled ICs in `components/ic/`)
- `src/digsim/app/` — GUI application (`cli.py` entry point, `gui/`, `gui_objects/`,
  `model/`, `settings/`)
- `src/digsim/synth/` — Yosys synthesis helper (`python -m digsim.synth`)
- `src/digsim/storage_model/` — pydantic models for saving/loading circuits
- `src/digsim/utils/` — Yosys netlist parsing
- `tests/` — pytest suite
- `examples/` — runnable examples, incl. pytest testbenches in `examples/pytest_tb/`
- `example_circuits/` — circuits for the GUI
- `docs/` — user documentation, published to https://freand76.github.io/digsim/ with
  MkDocs Material (`mkdocs.yml`). `docs/documentation.md` is only a pointer to the site.

Python >= 3.11 is supported (CI tests 3.11–3.14), so don't use newer-only syntax.
Dependencies in `pyproject.toml` are pinned to exact versions.

## Tooling

Use `uv` for everything. Ruff runs via `uv tool run`, not as a project dependency.

```sh
uv tool run ruff format          # format
uv tool run ruff check           # lint (add --fix for autofixes)
uv run --with pytest pytest      # run all tests (tests/ and examples/pytest_tb/)
uv run --with mypy mypy          # type check (config in pyproject.toml)
uv run -m digsim.app             # start the GUI
uv tool run --with mkdocs-material --with mkdocstrings-python --with ruff mkdocs build --strict   # check the docs build
uv run --with pytest python docs/scripts/generate_examples.py  # regenerate example images
uv run python docs/scripts/generate_tutorial.py  # regenerate GUI tutorial screenshots
```

The `uv_*.sh` scripts do the same in throwaway venvs (`uv_ruff.sh`, `uv_run_test.sh`,
`uv_run_app.sh`). Run ruff format + check, mypy and pytest before committing.

CI (`.github/workflows/`) runs ruff, and pytest plus `examples/yosys_counter/*.py` on Linux
(Python 3.11–3.14) and Windows. The test workflows run on push only, not on pull requests.
mypy is local only. The docs site is rebuilt and deployed by `docs.yaml` on every push to
`main` that touches `docs/`, `src/digsim/`, `mkdocs.yml` or `CHANGELOG.md` (included in the site's
Changelog page).

- CI runners can't load Qt's GUI libraries (no `libEGL`): tests must not import `QtGui` or
  `QtWidgets`. Keep testable logic in Qt-free modules (like `app/_desktop_entry.py`). The
  GUI has no automated tests, so check GUI changes by running the app (offscreen with
  `QT_QPA_PLATFORM=offscreen` for scripted checks).
- Ruff 0.17 also formats Python code blocks in Markdown files, and CI checks that.
- Documentation prose doesn't use semicolons unless one is really called for. Split the
  sentence or join the parts with a word instead. Code examples are exempt.
- Component images in `docs/images/components/` are copies of
  `src/digsim/app/gui_objects/images/` (except `LedBar.png`, a screenshot of the drawn
  component), and `docs/images/app_icon.png` of `src/digsim/app/images/app_icon.png`.
- The API Reference (`docs/api/`) is generated from the docstrings with mkdocstrings. Public
  classes and methods use Google style docstrings, and components list their ports under
  `Ports:` (they are created at runtime, so only the docstring can show them). The API pages
  list the members to show, so the reference only has the supported API: add a new public
  method there, and leave out internal plumbing that is only public by name.
- `docs/components.md` (Python) and `docs/gui-components.md` (GUI) walk through the real
  `XNOR` and `LedBar` code. Keep them in sync when changing them. Regenerate the example
  images when an example changes.

Ruff config is in `pyproject.toml`: line length 99, isort with PySide6 imports in their
own section and two blank lines after imports, no relative imports from parent packages.

## Code conventions

- Each source file starts with the copyright header
  `# Copyright (c) Fredrik Andersson, 2023-2025` / `# All rights reserved`, followed by a
  module docstring.
- Private modules are prefixed `_` and re-exported through the package `__init__.py`.
- Everything is type annotated. mypy runs with `disallow_untyped_defs`, so new functions need
  full signatures. Component ports are attached at runtime and typed via
  `Component.__getattr__`, and GUI objects narrow their `component` property to the concrete
  type.
- Use fully qualified Qt enums (`Qt.GlobalColor.red`, not `Qt.red`), and pass `int()` to Qt
  APIs that only take ints.

## Things that have bitten before

- **Simulation core**: changes to `circuit/` (events, ports, VCD) must keep every example's
  output and VCD files byte-identical, including the order of events at the same time:
  Yosys gate-level designs have races where that order is visible. Compare before/after.
  Don't change class attributes of hot classes (like `Port`) repeatedly at runtime: after
  enough changes CPython stops optimizing attribute access on that class.
- **GUI threading**: the model's signals are emitted from the simulation thread, so they are
  queued. GUI objects must not connect to model signals themselves, since a queued call to a
  removed object runs on freed memory. The circuit area receives them and forwards them to
  the current objects.
- **Yosys** runs in-process (`yowasp_yosys.run_yosys`, WebAssembly) unless a native `yosys`
  is on `PATH`. In the sandbox `/tmp` is a private folder, so work files go in a temp
  folder in the user cache. Paths given to Yosys must use forward slashes (`C:/...` on
  Windows). After a failed run, Yosys keeps its files open until garbage collection, which
  breaks cleanup on Windows. Things like this only show up in the Windows CI.

## Releases

1. Bump `version` in `pyproject.toml` and turn the `## vx.x.x` heading in
   `CHANGELOG.md` into the new version ("Prepare for release x.y.z" commit).
2. `bash create_dist_pkg.sh` builds sdist + wheel into `dist/` (it also regenerates
   `requirements.txt` with pip-compile).
3. Uploading to PyPI with `twine upload dist/*` is **always done manually by the
   maintainer**. Never run twine or upload anything yourself.

Add user-visible changes to the `## vx.x.x` section at the top of `CHANGELOG.md`.

## Commits

- One commit per single-purpose change. Don't bundle unrelated fixes, even small ones.
- Commit messages are tight and answer **why**: what was wrong or missing for the
  user, not how the code changes. Imperative subject line, short body.
- **Never** add a `Co-Authored-By` trailer or any other attribution line.
- Don't amend a pushed commit unless asked. A follow-up fix is a new commit.
- Commit only when asked, or as part of a task that asks for commits. Push only when
  asked, and ask before a force push.
- Never commit the untracked files in the root.
