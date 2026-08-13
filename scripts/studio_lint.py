#!/usr/bin/env python3
"""Validate an ai-short-drama Studio Plan JSON file.

Examples:
    python studio_lint.py studio-plan.json
    python studio_lint.py studio-plan.json --studio-ready --json
    Get-Content studio-plan.json -Raw | python studio_lint.py -
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ENTITY_ID = re.compile(r"^[a-z][a-z0-9_]*$")
IDENTITY_VIEWS = {"front_closeup", "front_full", "side_full"}
FORMAT_CONTRACTS = {
    "serial_episode": ("episode", "timeline"),
    "micro_drama": ("complete_micro_story", "timeline"),
    "viral_one_take": ("single_high_impact_moment", "one_take"),
    "grid_moment": ("single_high_impact_moment", "grid"),
    "continuous_long_take": ("scene", "one_take"),
}


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


def positive_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value > 0
    )


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


def require_strings(
    obj: dict[str, Any], fields: list[str], path: str, report: Report
) -> None:
    for field in fields:
        if not nonempty_string(obj.get(field)):
            report.error(f"{path}.{field}", "must be a non-empty string")


def validate_format(profile: dict[str, Any], report: Report) -> tuple[str, float]:
    require_strings(
        profile,
        ["id", "story_scope", "shot_strategy", "dominant_turn"],
        "format_profile",
        report,
    )
    format_id = profile.get("id")
    target = profile.get("target_duration_seconds")
    if not positive_number(target):
        report.error("format_profile.target_duration_seconds", "must be a positive number")
        target = 0.0

    if format_id not in FORMAT_CONTRACTS:
        report.error("format_profile.id", f"unknown format profile: {format_id!r}")
        return "", float(target)

    expected_scope, expected_strategy = FORMAT_CONTRACTS[format_id]
    if profile.get("story_scope") != expected_scope:
        report.error(
            "format_profile.story_scope",
            f"{format_id} requires {expected_scope}",
        )
    if profile.get("shot_strategy") != expected_strategy:
        report.error(
            "format_profile.shot_strategy",
            f"{format_id} requires {expected_strategy}",
        )
    if format_id in {"viral_one_take", "grid_moment"} and target > 30:
        report.warning(
            "format_profile.target_duration_seconds",
            "a single high-impact moment above 30 seconds may be carrying a full story",
        )
    return format_id, float(target)


def validate_capability(
    capability: dict[str, Any], studio_ready: bool, report: Report
) -> tuple[float, int]:
    require_strings(
        capability,
        ["model_id", "status", "verified_at", "evidence"],
        "model_capability",
        report,
    )
    max_duration = capability.get("max_duration_seconds")
    if not positive_number(max_duration):
        report.error("model_capability.max_duration_seconds", "must be a positive number")
        max_duration = 0.0

    max_refs = capability.get("max_reference_assets")
    if not isinstance(max_refs, int) or isinstance(max_refs, bool) or max_refs < 0:
        report.error(
            "model_capability.max_reference_assets",
            "must be a non-negative integer",
        )
        max_refs = 0

    supported = capability.get("supported_reference_types")
    if not isinstance(supported, list) or not supported:
        report.error(
            "model_capability.supported_reference_types",
            "must be a non-empty array",
        )
    if capability.get("status") not in {"verified", "unverified"}:
        report.error("model_capability.status", "must be verified or unverified")
    elif studio_ready and capability.get("status") != "verified":
        report.error(
            "model_capability.status",
            "must be verified in --studio-ready mode; run a capability probe first",
        )
    return float(max_duration), max_refs


def validate_globals(settings: dict[str, Any], report: Report) -> None:
    require_strings(
        settings,
        [
            "aspect_ratio",
            "visual_style",
            "lighting",
            "color_tone",
            "language",
            "audio_baseline",
        ],
        "global_settings",
        report,
    )


def validate_assets(
    assets: list[Any], studio_ready: bool, max_refs: int, report: Report
) -> tuple[set[str], set[str], set[str], set[str]]:
    asset_ids: set[str] = set()
    character_ids: set[str] = set()
    location_ids: set[str] = set()
    reference_files: set[str] = set()

    if not assets:
        report.error("assets", "must contain at least one asset")

    for index, raw in enumerate(assets):
        path = f"assets[{index}]"
        if not isinstance(raw, dict):
            report.error(path, "must be an object")
            continue
        require_strings(raw, ["id", "kind", "name", "recurrence"], path, report)
        asset_id = raw.get("id")
        kind = raw.get("kind")
        recurrence = raw.get("recurrence")
        if nonempty_string(asset_id):
            if not ENTITY_ID.match(asset_id):
                report.error(f"{path}.id", "must use lowercase ASCII letters, digits, and underscores")
            if asset_id in asset_ids:
                report.error(f"{path}.id", f"duplicate asset id: {asset_id}")
            asset_ids.add(asset_id)
            if kind == "character":
                character_ids.add(asset_id)
            if kind == "location":
                location_ids.add(asset_id)

        if kind not in {"character", "location", "prop", "costume", "voice"}:
            report.error(f"{path}.kind", f"unknown asset kind: {kind!r}")
        if recurrence not in {"recurring", "one_off"}:
            report.error(f"{path}.recurrence", "must be recurring or one_off")

        refs = raw.get("reference_files")
        if not isinstance(refs, list):
            report.error(f"{path}.reference_files", "must be an array")
            refs = []
        for ref_index, ref in enumerate(refs):
            if not nonempty_string(ref):
                report.error(
                    f"{path}.reference_files[{ref_index}]",
                    "must be a non-empty string",
                )
            else:
                reference_files.add(ref)

        if studio_ready and recurrence == "recurring":
            if not nonempty_string(raw.get("visual_anchor")):
                report.error(f"{path}.visual_anchor", "required for a recurring asset")
            if not refs:
                report.error(f"{path}.reference_files", "required for a recurring asset")

        if studio_ready and kind == "character" and recurrence == "recurring":
            views = raw.get("identity_views")
            if not isinstance(views, list):
                report.error(f"{path}.identity_views", "must be an array")
                views = []
            missing_views = sorted(IDENTITY_VIEWS - set(views))
            if missing_views:
                report.error(
                    f"{path}.identity_views",
                    "missing identity views: " + ", ".join(missing_views),
                )
            if not nonempty_string(raw.get("voice_anchor")):
                report.error(f"{path}.voice_anchor", "required for a recurring character")
            if raw.get("consent_status") != "verified":
                report.error(
                    f"{path}.consent_status",
                    "must be verified for a recurring character voice",
                )

    if len(reference_files) > max_refs:
        report.error(
            "assets[*].reference_files",
            f"uses {len(reference_files)} unique references, above model limit {max_refs}",
        )
    return asset_ids, character_ids, location_ids, reference_files


def validate_timeline(
    timeline: list[Any],
    target: float,
    max_duration: float,
    format_id: str,
    asset_ids: set[str],
    character_ids: set[str],
    location_ids: set[str],
    report: Report,
) -> None:
    if not timeline:
        report.error("timeline", "must contain at least one shot or beat")
        return

    if format_id == "grid_moment" and not 2 <= len(timeline) <= 24:
        report.error("timeline", "grid_moment must contain 2 to 24 panels")

    seen_ids: set[str] = set()
    expected_start = 0.0
    for index, raw in enumerate(timeline):
        path = f"timeline[{index}]"
        if not isinstance(raw, dict):
            report.error(path, "must be an object")
            continue
        require_strings(
            raw,
            [
                "id",
                "shot_size",
                "camera_move",
                "angle",
                "location_id",
                "emotion",
                "transition",
                "observable_action",
                "sound",
            ],
            path,
            report,
        )
        shot_id = raw.get("id")
        if nonempty_string(shot_id):
            if not ENTITY_ID.match(shot_id):
                report.error(f"{path}.id", "must use lowercase ASCII letters, digits, and underscores")
            if shot_id in seen_ids:
                report.error(f"{path}.id", f"duplicate timeline id: {shot_id}")
            seen_ids.add(shot_id)

        start = raw.get("start_seconds")
        duration = raw.get("duration_seconds")
        if not isinstance(start, (int, float)) or isinstance(start, bool) or start < 0:
            report.error(f"{path}.start_seconds", "must be a non-negative number")
            start = expected_start
        if not positive_number(duration):
            report.error(f"{path}.duration_seconds", "must be a positive number")
            duration = 0.0
        if abs(float(start) - expected_start) > 0.05:
            report.error(
                f"{path}.start_seconds",
                f"must be contiguous; expected {expected_start:g}",
            )
        if max_duration and duration > max_duration:
            report.error(
                f"{path}.duration_seconds",
                f"{duration:g}s exceeds model limit {max_duration:g}s",
            )
        expected_start = float(start) + float(duration)

        location_id = raw.get("location_id")
        if nonempty_string(location_id) and location_id not in location_ids:
            report.error(f"{path}.location_id", f"unknown location asset: {location_id}")

        entity_ids = raw.get("entity_ids")
        if not isinstance(entity_ids, list):
            report.error(f"{path}.entity_ids", "must be an array")
            entity_ids = []
        for entity_index, entity_id in enumerate(entity_ids):
            if entity_id not in asset_ids:
                report.error(
                    f"{path}.entity_ids[{entity_index}]",
                    f"unknown asset: {entity_id}",
                )

        dialogue = raw.get("dialogue")
        if not isinstance(dialogue, list):
            report.error(f"{path}.dialogue", "must be an array")
            dialogue = []
        for line_index, line in enumerate(dialogue):
            line_path = f"{path}.dialogue[{line_index}]"
            if not isinstance(line, dict):
                report.error(line_path, "must be an object")
                continue
            require_strings(line, ["speaker_id", "text", "performance"], line_path, report)
            speaker_id = line.get("speaker_id")
            if nonempty_string(speaker_id) and speaker_id not in character_ids:
                report.error(f"{line_path}.speaker_id", f"unknown character: {speaker_id}")

        if format_id in {"viral_one_take", "continuous_long_take"}:
            allowed = {"none"} if index == 0 else {"continuous"}
            if raw.get("transition") not in allowed:
                report.error(
                    f"{path}.transition",
                    "one-take formats require none on the first beat and continuous thereafter",
                )

    if abs(expected_start - target) > 0.1:
        report.error(
            "timeline",
            f"ends at {expected_start:g}s but target duration is {target:g}s",
        )
    if format_id in {"viral_one_take", "continuous_long_take"} and max_duration:
        if target > max_duration:
            report.error(
                "format_profile.target_duration_seconds",
                f"one-take duration {target:g}s exceeds model limit {max_duration:g}s",
            )


def validate_variation(policy: dict[str, Any], studio_ready: bool, report: Report) -> None:
    seed = policy.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        report.error("variation_policy.seed", "must be an integer")
    dimensions = policy.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        report.error("variation_policy.dimensions", "must be a non-empty array")
    elif any(not nonempty_string(item) for item in dimensions):
        report.error("variation_policy.dimensions", "must contain non-empty strings")
    shuffle_bag = policy.get("shuffle_bag")
    if not isinstance(shuffle_bag, bool):
        report.error("variation_policy.shuffle_bag", "must be a boolean")
    avoid_recent = policy.get("avoid_recent")
    if not isinstance(avoid_recent, int) or isinstance(avoid_recent, bool) or avoid_recent < 0:
        report.error("variation_policy.avoid_recent", "must be a non-negative integer")
    if studio_ready and shuffle_bag is not True:
        report.warning(
            "variation_policy.shuffle_bag",
            "disabled; batch presets may repeat before the candidate bag is exhausted",
        )
    if shuffle_bag is True and avoid_recent == 0:
        report.warning(
            "variation_policy.avoid_recent",
            "zero allows immediate preset repetition",
        )


def validate_outputs(outputs: dict[str, Any], report: Report) -> None:
    require_strings(
        outputs,
        ["prompt_mode", "draft_path", "asset_inbox", "editor_handoff"],
        "outputs",
        report,
    )
    if outputs.get("prompt_mode") not in {"long_timeline", "shot_by_shot", "both"}:
        report.error(
            "outputs.prompt_mode",
            "must be long_timeline, shot_by_shot, or both",
        )


def lint(data: Any, studio_ready: bool) -> Report:
    report = Report()
    if not isinstance(data, dict):
        report.error("$", "top-level JSON value must be an object")
        return report

    profile = require_object(data, "format_profile", report)
    capability = require_object(data, "model_capability", report)
    globals_ = require_object(data, "global_settings", report)
    assets = require_list(data, "assets", report)
    timeline = require_list(data, "timeline", report)
    variation = require_object(data, "variation_policy", report)
    outputs = require_object(data, "outputs", report)

    format_id, target = validate_format(profile, report)
    max_duration, max_refs = validate_capability(capability, studio_ready, report)
    validate_globals(globals_, report)
    asset_ids, character_ids, location_ids, _refs = validate_assets(
        assets, studio_ready, max_refs, report
    )
    validate_timeline(
        timeline,
        target,
        max_duration,
        format_id,
        asset_ids,
        character_ids,
        location_ids,
        report,
    )
    validate_variation(variation, studio_ready, report)
    validate_outputs(outputs, report)
    return report


def read_json(source: str) -> Any:
    if source == "-":
        raw = sys.stdin.read()
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
        "--studio-ready",
        action="store_true",
        help="require verified capability, recurring asset anchors, identity views, and consent",
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = read_json(args.source)
    except (OSError, json.JSONDecodeError) as exc:
        report = Report()
        report.error("$", f"cannot read valid JSON: {exc}")
        emit(report, args.json)
        return 1

    report = lint(data, args.studio_ready)
    emit(report, args.json)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
