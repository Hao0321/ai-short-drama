#!/usr/bin/env python3
"""Validate an ai-short-drama production-pack JSON file.

Examples:
    python drama_lint.py production-pack.json
    python drama_lint.py production-pack.json --production-ready --json
    python drama_lint.py - < pack.json

Windows PowerShell 5.1 pipes text to native programs as ASCII by default, so
pass the file path, or pipe with UTF-8 explicitly:
    $OutputEncoding = [Text.UTF8Encoding]::new($false)
    Get-Content pack.json -Raw -Encoding UTF8 | python drama_lint.py -
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


EPISODE_ID = re.compile(r"^ep_(\d+)$")
ENTITY_ID = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class Finding:
    level: str
    path: str
    message: str


class Report:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def error(self, path: str, message: str) -> None:
        self.findings.append(Finding("error", path, message))

    def warning(self, path: str, message: str) -> None:
        self.findings.append(Finding("warning", path, message))

    @property
    def errors(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [item for item in self.findings if item.level == "warning"]


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_object(parent: dict[str, Any], key: str, report: Report) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        report.error(key, "must be an object")
        return {}
    return value


def require_list(parent: dict[str, Any], key: str, report: Report) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        report.error(key, "must be an array")
        return []
    return value


def require_fields(
    obj: dict[str, Any], fields: list[str], path: str, report: Report
) -> None:
    for field in fields:
        if not nonempty_string(obj.get(field)):
            report.error(f"{path}.{field}", "must be a non-empty string")


def validate_project(project: dict[str, Any], episode_count: int, report: Report) -> int:
    require_fields(project, ["title", "market", "format"], "project", report)

    duration = project.get("episode_duration_seconds")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        report.error("project.episode_duration_seconds", "must be a positive number")

    planned = project.get("planned_episodes")
    if not isinstance(planned, int) or isinstance(planned, bool) or planned <= 0:
        report.error("project.planned_episodes", "must be a positive integer")
        return 0
    if planned < episode_count:
        report.error(
            "project.planned_episodes",
            f"is {planned}, smaller than the {episode_count} supplied episodes",
        )
    return planned


def validate_premise(premise: dict[str, Any], report: Report) -> None:
    require_fields(
        premise,
        [
            "public_identity",
            "hidden_truth",
            "engine",
            "season_question",
            "fresh_twist",
        ],
        "premise_contract",
        report,
    )
    if premise.get("public_identity") == premise.get("hidden_truth"):
        report.warning(
            "premise_contract.hidden_truth",
            "is identical to public_identity; the premise may lack an information gap",
        )


def validate_entities(
    items: list[Any],
    kind: str,
    required: list[str],
    production_ready: bool,
    report: Report,
) -> set[str]:
    seen: set[str] = set()
    ids: set[str] = set()
    for index, raw in enumerate(items):
        path = f"{kind}[{index}]"
        if not isinstance(raw, dict):
            report.error(path, "must be an object")
            continue
        require_fields(raw, ["id", "name", *required], path, report)
        entity_id = raw.get("id")
        if not nonempty_string(entity_id):
            continue
        if not ENTITY_ID.match(entity_id):
            report.error(f"{path}.id", "must use lowercase ASCII letters, digits, and underscores")
        if entity_id in seen:
            report.error(f"{path}.id", f"duplicate id: {entity_id}")
        seen.add(entity_id)
        ids.add(entity_id)

        if production_ready:
            if not nonempty_string(raw.get("visual_anchor")):
                report.error(f"{path}.visual_anchor", "required in --production-ready mode")
            if kind == "characters" and not nonempty_string(raw.get("voice_anchor")):
                report.error(f"{path}.voice_anchor", "required in --production-ready mode")
    return ids


def parse_episode_id(value: Any, path: str, report: Report) -> int | None:
    if not nonempty_string(value):
        report.error(path, "must be a non-empty string")
        return None
    match = EPISODE_ID.match(value)
    if not match:
        report.error(path, "must match ep_001, ep_002, ...")
        return None
    return int(match.group(1))


def validate_reference_list(
    episode: dict[str, Any],
    key: str,
    valid_ids: set[str],
    path: str,
    production_ready: bool,
    report: Report,
) -> None:
    values = episode.get(key)
    if not isinstance(values, list):
        report.error(f"{path}.{key}", "must be an array of entity ids")
        return
    if production_ready and not values:
        report.error(f"{path}.{key}", "must not be empty in --production-ready mode")
    for index, value in enumerate(values):
        item_path = f"{path}.{key}[{index}]"
        if not nonempty_string(value):
            report.error(item_path, "must be a non-empty string")
        elif value not in valid_ids:
            report.error(item_path, f"unknown {key[:-1]} id: {value}")


def validate_state_delta(
    episode: dict[str, Any], path: str, production_ready: bool, report: Report
) -> None:
    delta = episode.get("state_delta")
    if not isinstance(delta, list):
        report.error(f"{path}.state_delta", "must be an array")
        return
    if production_ready and not delta:
        report.error(f"{path}.state_delta", "must not be empty in --production-ready mode")
    for index, item in enumerate(delta):
        if not nonempty_string(item):
            report.error(f"{path}.state_delta[{index}]", "must be a non-empty string")


def validate_debt_arrays(
    episode: dict[str, Any],
    episode_number: int,
    path: str,
    planned: int,
    openings: dict[str, tuple[int, int]],
    payments: list[tuple[str, int, str]],
    report: Report,
) -> None:
    opened = episode.get("debts_opened")
    if not isinstance(opened, list):
        report.error(f"{path}.debts_opened", "must be an array")
    else:
        for index, raw in enumerate(opened):
            debt_path = f"{path}.debts_opened[{index}]"
            if not isinstance(raw, dict):
                report.error(debt_path, "must be an object with id and due_episode")
                continue
            debt_id = raw.get("id")
            due = raw.get("due_episode")
            if not nonempty_string(debt_id):
                report.error(f"{debt_path}.id", "must be a non-empty string")
                continue
            if debt_id in openings:
                report.error(f"{debt_path}.id", f"debt already opened: {debt_id}")
            if not isinstance(due, int) or isinstance(due, bool):
                report.error(f"{debt_path}.due_episode", "must be an integer")
                continue
            if due < episode_number:
                report.error(
                    f"{debt_path}.due_episode",
                    "cannot be earlier than the episode that opens the debt",
                )
            if planned and due > planned:
                report.error(
                    f"{debt_path}.due_episode",
                    f"cannot exceed planned_episodes ({planned})",
                )
            openings[debt_id] = (episode_number, due)

    paid = episode.get("debts_paid")
    if not isinstance(paid, list):
        report.error(f"{path}.debts_paid", "must be an array of debt ids")
    else:
        for index, debt_id in enumerate(paid):
            pay_path = f"{path}.debts_paid[{index}]"
            if not nonempty_string(debt_id):
                report.error(pay_path, "must be a non-empty string")
                continue
            payments.append((debt_id, episode_number, pay_path))


def validate_episodes(
    episodes: list[Any],
    character_ids: set[str],
    location_ids: set[str],
    planned: int,
    production_ready: bool,
    report: Report,
) -> None:
    numbers: list[int] = []
    seen_ids: set[str] = set()
    openings: dict[str, tuple[int, int]] = {}
    payments: list[tuple[str, int, str]] = []

    for index, raw in enumerate(episodes):
        path = f"episodes[{index}]"
        if not isinstance(raw, dict):
            report.error(path, "must be an object")
            continue

        number = parse_episode_id(raw.get("id"), f"{path}.id", report)
        if number is None:
            continue
        numbers.append(number)
        episode_id = raw["id"]
        if episode_id in seen_ids:
            report.error(f"{path}.id", f"duplicate episode id: {episode_id}")
        seen_ids.add(episode_id)

        require_fields(raw, ["hook", "turn", "cliffhanger"], path, report)
        if not nonempty_string(raw.get("payoff")) and not nonempty_string(raw.get("progress")):
            report.error(path, "must include a non-empty payoff or progress")

        validate_reference_list(
            raw, "characters", character_ids, path, production_ready, report
        )
        validate_reference_list(
            raw, "locations", location_ids, path, production_ready, report
        )
        validate_state_delta(raw, path, production_ready, report)
        validate_debt_arrays(
            raw, number, path, planned, openings, payments, report
        )

    if numbers:
        if numbers != sorted(numbers):
            report.error("episodes", "must be sorted by ascending episode id")
        expected = list(range(numbers[0], numbers[0] + len(numbers)))
        if sorted(numbers) != expected:
            report.error("episodes", "episode ids must be consecutive within the supplied pack")
        if numbers[0] != 1:
            report.warning("episodes[0].id", "pack does not start at ep_001")

    paid_once: set[str] = set()
    latest_supplied = max(numbers, default=0)
    for debt_id, paid_episode, path in payments:
        if debt_id not in openings:
            report.error(path, f"pays unknown debt: {debt_id}")
            continue
        open_episode, due_episode = openings[debt_id]
        if paid_episode < open_episode:
            report.error(path, f"pays debt before it opens in ep_{open_episode:03d}")
        if paid_episode > due_episode:
            report.warning(path, f"pays debt after its due episode ({due_episode})")
        if debt_id in paid_once:
            report.error(path, f"debt paid more than once: {debt_id}")
        paid_once.add(debt_id)

    for debt_id, (_open_episode, due_episode) in openings.items():
        if due_episode <= latest_supplied and debt_id not in paid_once:
            report.warning(
                "episodes",
                f"debt {debt_id} is due by ep_{due_episode:03d} but is unpaid in this pack",
            )


def lint(data: Any, production_ready: bool) -> Report:
    report = Report()
    if not isinstance(data, dict):
        report.error("$", "top-level JSON value must be an object")
        return report

    episodes = require_list(data, "episodes", report)
    project = require_object(data, "project", report)
    premise = require_object(data, "premise_contract", report)
    characters = require_list(data, "characters", report)
    locations = require_list(data, "locations", report)

    if not episodes:
        report.error("episodes", "must contain at least one episode")

    planned = validate_project(project, len(episodes), report)
    validate_premise(premise, report)
    character_ids = validate_entities(
        characters,
        "characters",
        ["public_identity", "hidden_truth"],
        production_ready,
        report,
    )
    location_ids = validate_entities(
        locations, "locations", [], production_ready, report
    )
    validate_episodes(
        episodes,
        character_ids,
        location_ids,
        planned,
        production_ready,
        report,
    )
    return report


def read_json(source: str) -> Any:
    if source == "-":
        # Same codec as the file branch; the locale codec (cp950, cp1252) and a BOM break JSON.
        raw = sys.stdin.buffer.read().decode("utf-8-sig")
    else:
        raw = Path(source).read_text(encoding="utf-8-sig")
    return json.loads(raw)


def emit(report: Report, as_json: bool) -> None:
    if as_json:
        payload = {
            "valid": not report.errors,
            "error_count": len(report.errors),
            "warning_count": len(report.warnings),
            "findings": [asdict(item) for item in report.findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status = "VALID" if not report.errors else "INVALID"
    print(f"{status}: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    for item in report.findings:
        print(f"[{item.level.upper()}] {item.path}: {item.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="JSON file path, or - for stdin")
    parser.add_argument(
        "--production-ready",
        action="store_true",
        help="require visual/voice anchors, entity references, and state deltas",
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    return parser.parse_args()


def use_utf8_output() -> None:
    """Captured output on Windows defaults to the locale codec, which cannot encode
    Simplified Chinese or emoji in findings; reports are always UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main() -> int:
    use_utf8_output()
    args = parse_args()
    try:
        data = read_json(args.source)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        report = Report()
        report.error("$", f"cannot read valid JSON: {exc}")
        emit(report, args.json)
        return 1

    report = lint(data, args.production_ready)
    emit(report, args.json)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
