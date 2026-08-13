from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "studio_lint", ROOT / "scripts" / "studio_lint.py"
)
assert SPEC and SPEC.loader
STUDIO_LINT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STUDIO_LINT
SPEC.loader.exec_module(STUDIO_LINT)


def valid_plan() -> dict:
    return {
        "format_profile": {
            "id": "viral_one_take",
            "story_scope": "single_high_impact_moment",
            "target_duration_seconds": 10,
            "shot_strategy": "one_take",
            "dominant_turn": "The locked door opens from the inside.",
        },
        "model_capability": {
            "model_id": "example/video/v1",
            "status": "verified",
            "max_duration_seconds": 10,
            "max_reference_assets": 4,
            "supported_reference_types": ["image"],
            "verified_at": "2026-08-13",
            "evidence": "official documentation checked for this run",
        },
        "global_settings": {
            "aspect_ratio": "9:16",
            "visual_style": "cinematic grounded realism",
            "lighting": "motivated practical lighting",
            "color_tone": "warm skin and cool shadows",
            "language": "zh-TW",
            "audio_baseline": "dialogue-forward controlled room tone",
        },
        "assets": [
            {
                "id": "char_lead_01",
                "kind": "character",
                "name": "lead",
                "recurrence": "recurring",
                "visual_anchor": "approved character sheet v1",
                "voice_anchor": "licensed voice profile v1",
                "consent_status": "verified",
                "identity_views": ["front_closeup", "front_full", "side_full"],
                "reference_files": ["lead_close.png", "lead_front.png", "lead_side.png"],
            },
            {
                "id": "loc_hall_01",
                "kind": "location",
                "name": "hallway",
                "recurrence": "recurring",
                "visual_anchor": "approved location sheet v1",
                "consent_status": "not_applicable",
                "identity_views": [],
                "reference_files": ["hall.png"],
            },
        ],
        "timeline": [
            {
                "id": "beat_001",
                "start_seconds": 0,
                "duration_seconds": 4,
                "shot_size": "medium",
                "camera_move": "slow_track_back",
                "angle": "eye_level",
                "location_id": "loc_hall_01",
                "emotion": "contained_panic",
                "transition": "none",
                "entity_ids": ["char_lead_01"],
                "observable_action": "The lead backs toward the locked door.",
                "dialogue": [],
                "sound": "Footsteps approach through the hallway.",
            },
            {
                "id": "beat_002",
                "start_seconds": 4,
                "duration_seconds": 6,
                "shot_size": "closeup",
                "camera_move": "continuous_orbit",
                "angle": "slightly_low",
                "location_id": "loc_hall_01",
                "emotion": "shock",
                "transition": "continuous",
                "entity_ids": ["char_lead_01"],
                "observable_action": "The door opens inward and the lead stops mid-step.",
                "dialogue": [
                    {
                        "speaker_id": "char_lead_01",
                        "text": "You were inside?",
                        "performance": "barely audible",
                    }
                ],
                "sound": "The latch clicks under the approaching footsteps.",
            },
        ],
        "variation_policy": {
            "seed": 1847,
            "dimensions": ["pace", "dialogue_density"],
            "shuffle_bag": True,
            "avoid_recent": 3,
        },
        "outputs": {
            "prompt_mode": "both",
            "draft_path": "projects/demo/studio-plan.json",
            "asset_inbox": "projects/demo/assets/inbox",
            "editor_handoff": "9:16 timeline with captions, dialogue, SFX, and QA notes",
        },
    }


class StudioLintTests(unittest.TestCase):
    def test_valid_studio_ready_plan(self) -> None:
        report = STUDIO_LINT.lint(valid_plan(), studio_ready=True)
        self.assertEqual([], report.errors)

    def test_rejects_reference_overflow(self) -> None:
        plan = valid_plan()
        plan["model_capability"]["max_reference_assets"] = 3
        report = STUDIO_LINT.lint(plan, studio_ready=True)
        self.assertTrue(any("above model limit" in item.message for item in report.errors))

    def test_rejects_missing_identity_view_and_unverified_model(self) -> None:
        plan = valid_plan()
        plan["assets"][0]["identity_views"] = ["front_closeup"]
        plan["model_capability"]["status"] = "unverified"
        report = STUDIO_LINT.lint(plan, studio_ready=True)
        messages = [item.message for item in report.errors]
        self.assertTrue(any("missing identity views" in message for message in messages))
        self.assertTrue(any("capability probe" in message for message in messages))

    def test_rejects_non_contiguous_timeline(self) -> None:
        plan = valid_plan()
        plan["timeline"][1]["start_seconds"] = 5
        report = STUDIO_LINT.lint(plan, studio_ready=True)
        self.assertTrue(any("must be contiguous" in item.message for item in report.errors))

    def test_schema_is_valid_json(self) -> None:
        schema_path = ROOT / "scripts" / "studio_plan.schema.json"
        with schema_path.open(encoding="utf-8") as stream:
            schema = json.load(stream)
        self.assertEqual("AI Short Drama Studio Plan", schema["title"])

    def test_lint_does_not_mutate_input(self) -> None:
        plan = valid_plan()
        original = copy.deepcopy(plan)
        STUDIO_LINT.lint(plan, studio_ready=True)
        self.assertEqual(original, plan)


if __name__ == "__main__":
    unittest.main()
