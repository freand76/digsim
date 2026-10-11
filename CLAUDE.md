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
- `tests/` — pytest suite; `examples/` — runnable examples, incl. pytest testbenches
  in `examples/pytest_tb/`; `example_circuits/` — circuits for the GUI
- `docs/` — user documentation, published to https://freand76.github.io/digsim/ with
  MkDocs Material (`mkdocs.yml`). `docs/documentation.md` is only a pointer to the site.

Python >= 3.10 is supported (CI tests 3.10–3.14), so don't use newer-only syntax.
Dependencies in `pyproject.toml` are pinned to exact versions.

## Tooling

Use `uv` for everything. Ruff runs via `uv tool run`, not as a project dependency.

```sh
uv tool run ruff format          # format
uv tool run ruff check           # lint (add --fix for autofixes)
uv run --with pytest pytest      # run all tests (tests/ and examples/pytest_tb/)
uv run --with mypy --with types-pexpect mypy   # type check (config in pyproject.toml)
uv run -m digsim.app             # start the GUI
uv tool run --with mkdocs-material mkdocs build --strict   # check the docs build
```

The `uv_*.sh` scripts do the same in throwaway venvs (`uv_ruff.sh`, `uv_run_test.sh`,
`uv_run_app.sh`). Run ruff format + check, mypy and pytest before committing. CI runs ruff
and pytest (`.github/workflows/`), plus `examples/yosys_counter/*.py`; mypy is local only. The docs site is
rebuilt and deployed by `.github/workflows/docs.yaml` on every push to `main` that touches
`docs/` or `mkdocs.yml`. Component images in `docs/images/components/` are copies of
`src/digsim/app/gui_objects/images/` (except `LedBar.png`, a screenshot of the drawn
component), and `docs/images/app_icon.png` of
`src/digsim/app/images/app_icon.png`.

Ruff config is in `pyproject.toml`: line length 99, isort with PySide6 imports in their
own section and two blank lines after imports, no relative imports from parent packages.

## Code conventions

- Each source file starts with the copyright header
  `# Copyright (c) Fredrik Andersson, 2023-2025` / `# All rights reserved`, followed by a
  module docstring.
- Private modules are prefixed `_` and re-exported through the package `__init__.py`.
- Everything is type annotated; mypy runs with `disallow_untyped_defs`, so new functions need
  full signatures. Component ports are attached at runtime and typed via
  `Component.__getattr__`; GUI objects narrow their `component` property to the concrete type.
- Use fully qualified Qt enums (`Qt.GlobalColor.red`, not `Qt.red`), and pass `int()` to Qt
  APIs that only take ints.

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
