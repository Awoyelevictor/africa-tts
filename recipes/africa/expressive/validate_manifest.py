#!/usr/bin/env python3
"""Validate annotated expressive-vocalisation JSONL without modifying source audio."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

EVENTS = {
    "sigh", "sniff", "laughter", "breathing", "gasp",
    "whisper", "throat_clear", "groan",
}
SPLITS = {"train", "validation", "test"}
POSITIONS = {"before", "during", "after"}


def validate(path: Path, audio_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    speaker_splits: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            prefix = f"line {line_no}"
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{prefix}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{prefix}: each JSONL row must be an object")
                continue

            for field in ("audio", "transcript", "language", "speaker_id", "split",
                          "license", "consent", "events"):
                if field not in row:
                    errors.append(f"{prefix}: missing required field '{field}'")

            audio = row.get("audio")
            if not isinstance(audio, str) or not audio.strip():
                errors.append(f"{prefix}: audio must be a non-empty relative path")
            elif Path(audio).is_absolute() or ".." in Path(audio).parts:
                errors.append(f"{prefix}: audio path must be relative and cannot traverse directories")
            elif audio_root is not None and not (audio_root / audio).is_file():
                errors.append(f"{prefix}: audio file not found: {audio}")

            if not isinstance(row.get("transcript"), str):
                errors.append(f"{prefix}: transcript must be a string (empty is allowed for event-only clips)")
            if not isinstance(row.get("language"), str) or not row.get("language", "").strip():
                errors.append(f"{prefix}: language must be a non-empty ISO language code")
            speaker = row.get("speaker_id")
            split = row.get("split")
            if not isinstance(speaker, str) or not speaker.strip():
                errors.append(f"{prefix}: speaker_id must be non-empty")
            elif split in SPLITS:
                speaker_splits[speaker].add(split)
            if split not in SPLITS:
                errors.append(f"{prefix}: split must be one of {sorted(SPLITS)}")
            if not isinstance(row.get("license"), str) or not row.get("license", "").strip():
                errors.append(f"{prefix}: license/source terms must be recorded")
            if row.get("consent") is not True:
                errors.append(f"{prefix}: consent must be explicitly true")

            events = row.get("events")
            if not isinstance(events, list):
                errors.append(f"{prefix}: events must be a list")
                continue
            spans = []
            for idx, event in enumerate(events):
                ep = f"{prefix}, event {idx}"
                if not isinstance(event, dict):
                    errors.append(f"{ep}: event must be an object")
                    continue
                kind = event.get("type")
                if kind not in EVENTS:
                    errors.append(f"{ep}: unsupported type {kind!r}; expected one of {sorted(EVENTS)}")
                start, end = event.get("start"), event.get("end")
                if (isinstance(start, bool) or not isinstance(start, (int, float))
                        or isinstance(end, bool) or not isinstance(end, (int, float))
                        or not math.isfinite(start) or not math.isfinite(end)
                        or start < 0 or end <= start):
                    errors.append(f"{ep}: start/end must be finite seconds with 0 <= start < end")
                else:
                    spans.append((float(start), float(end), idx))
                position = event.get("position")
                if position is not None and position not in POSITIONS:
                    errors.append(f"{ep}: position must be one of {sorted(POSITIONS)}")
            spans.sort()
            for left, right in zip(spans, spans[1:]):
                if right[0] < left[1]:
                    errors.append(f"{prefix}: events {left[2]} and {right[2]} overlap; verify intentional overlap")
    for speaker, splits in speaker_splits.items():
        if len(splits) > 1:
            errors.append(f"speaker {speaker!r} appears in multiple splits: {sorted(splits)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--audio-root", type=Path)
    args = parser.parse_args()
    errors = validate(args.manifest, args.audio_root)
    if errors:
        print(f"FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK: annotations in {args.manifest} passed validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
