"""Command-line entry point for meeting-notes-agent.

Usage:
    python -m app.cli sample_data/sample_transcript.txt --title "Q3 Planning Sync"
    python -m app.cli sample_data/sample_transcript.txt --format json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.extractor import build_meeting_notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract structured notes from a meeting transcript.")
    parser.add_argument("transcript", type=Path, help="Path to a plain-text transcript file")
    parser.add_argument("--title", default="Meeting Notes", help="Title for the meeting")
    parser.add_argument(
        "--format", choices=["markdown", "json"], default="markdown", help="Output format"
    )
    args = parser.parse_args(argv)

    if not args.transcript.exists():
        print(f"error: transcript file not found: {args.transcript}", file=sys.stderr)
        return 1

    raw_text = args.transcript.read_text(encoding="utf-8")
    notes = build_meeting_notes(raw_text, title=args.title)

    if args.format == "json":
        print(notes.model_dump_json(indent=2))
    else:
        print(notes.to_markdown())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
