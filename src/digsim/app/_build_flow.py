# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""
The steps of synthesizing a Verilog file in the editor, which a thread runs. No Qt, so
that it can be tested.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from digsim.circuit.components import YosysComponent
from digsim.circuit.components.atoms import DigsimException
from digsim.synth import Synthesis, SynthesisException, YosysMessage, parse_messages


StepStatus = Literal["running", "ok", "warning", "error", "skipped"]


@dataclass
class BuildStep:
    """A step of the build, sent when it starts (running) and when it ends"""

    name: str
    status: StepStatus
    detail: str = ""
    seconds: float | None = None


@dataclass
class BuildResult:
    """The netlists (None if the build failed), the Yosys log and its messages"""

    netlists: dict[bool, dict[str, Any]] | None = None
    log: list[str] = field(default_factory=list)
    messages: list[YosysMessage] = field(default_factory=list)

    def errors(self) -> list[YosysMessage]:
        """The error messages"""
        return [message for message in self.messages if message.kind == "error"]

    def warnings(self) -> list[YosysMessage]:
        """The warning messages"""
        return [message for message in self.messages if message.kind == "warning"]


def synth_step_name(functional: bool) -> str:
    """The name of the step that synthesizes into gates or functional blocks"""
    return "Synthesize into functional blocks" if functional else "Synthesize into gates"


def describe(message: YosysMessage) -> str:
    """A message, with its line"""
    if message.line is None:
        return message.text
    return f"Line {message.line}: {message.text}"


def _failed(exc: Exception, log: list[str]) -> list[YosysMessage]:
    """The messages of a failed step"""
    if isinstance(exc, SynthesisException):
        return exc.messages
    return [*parse_messages(log), YosysMessage("error", str(exc))]


def run_synthesis(
    path: str | Path, variants: set[bool], report: Callable[[BuildStep], None]
) -> BuildResult:
    """
    List the modules of a Verilog file, and synthesize it into gates (False) and into
    functional blocks (True), as 'variants' says. Each step is reported when it starts
    and when it ends. The netlists are kept for the components (see synthesize_file).
    """
    path = str(path)
    result = BuildResult()
    log = result.log

    def run(name: str, action: Callable[[], str]) -> bool:
        report(BuildStep(name, "running"))
        start = time.monotonic()
        before = len(parse_messages(log))
        try:
            detail = action()
        except (DigsimException, OSError) as exc:
            result.messages = _failed(exc, log)
            errors = result.errors()
            detail = describe(errors[0]) if errors else str(exc)
            report(BuildStep(name, "error", detail, time.monotonic() - start))
            return False
        warnings = len(parse_messages(log)) - before
        status: StepStatus = "warning" if warnings else "ok"
        if warnings:
            detail = f"{detail}, {warnings} warning{'s' if warnings > 1 else ''}".lstrip(", ")
        report(BuildStep(name, status, detail, time.monotonic() - start))
        return True

    modules: list[str] = []

    def list_modules() -> str:
        modules.extend(Synthesis.list_modules(path, log=log))
        if len(modules) != 1:
            raise SynthesisException(
                f"ERROR: The file has {len(modules)} modules, a Yosys component needs one", log
            )
        return f"Module {modules[0]}"

    if not run("List modules", list_modules):
        return result
    netlists: dict[bool, dict[str, Any]] = {}
    for variant in sorted(variants):

        def synthesize(variant: bool = variant) -> str:
            netlists[variant] = YosysComponent.synthesize_file(
                path, variant, log=log, cached=False, top=modules[0]
            )
            return ""

        if not run(synth_step_name(variant), synthesize):
            return result
    result.netlists = netlists
    result.messages = parse_messages(log)
    return result
