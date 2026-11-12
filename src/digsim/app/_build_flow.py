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

from digsim.circuit.components import YosysComponent, YosysVariant, file_modules, parameter_dict
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

    netlists: dict[YosysVariant, dict[str, Any]] | None = None
    log: list[str] = field(default_factory=list)
    messages: list[YosysMessage] = field(default_factory=list)

    def errors(self) -> list[YosysMessage]:
        """The error messages"""
        return [message for message in self.messages if message.kind == "error"]

    def warnings(self) -> list[YosysMessage]:
        """The warning messages"""
        return [message for message in self.messages if message.kind == "warning"]


def synth_step_name(variant: YosysVariant) -> str:
    """The name of the step that synthesizes into gates or functional blocks"""
    name = "Synthesize into functional blocks" if variant.functional else "Synthesize into gates"
    details = [f"module {variant.module}"] if variant.module else []
    if variant.parameters:
        details.append(variant.parameters.replace(",", ", "))
    if details:
        name += f" ({', '.join(details)})"
    return name


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
    path: str | Path, variants: set[YosysVariant], report: Callable[[BuildStep], None]
) -> BuildResult:
    """
    List the modules of a Verilog file, and synthesize its top module (or the module of a
    variant) into gates or functional blocks, with parameters, as 'variants' says. Each step is reported when it starts
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

    tops: list[str] = []

    def list_modules() -> str:
        hierarchy = file_modules(path, log)
        tops.extend(Synthesis.top_modules(hierarchy))
        chosen = sorted({variant.module for variant in variants if variant.module})
        for module in chosen:
            if module not in hierarchy:
                raise SynthesisException(f"ERROR: The file has no module '{module}'", log)
        if len(tops) != 1 and any(not variant.module for variant in variants):
            raise SynthesisException(
                f"ERROR: The file has {len(tops)} top modules ({', '.join(tops)}), choose "
                "the module of the component in its settings",
                log,
            )
        modules = chosen if all(variant.module for variant in variants) else [tops[0], *chosen]
        modules = list(dict.fromkeys(modules))
        return f"Module{'s' if len(modules) > 1 else ''} {', '.join(modules)}"

    if not run("List modules", list_modules):
        return result
    netlists: dict[YosysVariant, dict[str, Any]] = {}
    for variant in sorted(variants):

        def synthesize(variant: YosysVariant = variant) -> str:
            netlists[variant] = YosysComponent.synthesize_file(
                path,
                variant.functional,
                log=log,
                cached=False,
                top=variant.module or tops[0],
                parameters=parameter_dict(variant.parameters),
                module=variant.module,
            )
            return ""

        if not run(synth_step_name(variant), synthesize):
            return result
    result.netlists = netlists
    result.messages = parse_messages(log)
    return result
