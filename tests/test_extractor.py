from pathlib import Path

from app.extractor import (
    build_meeting_notes,
    extract_action_items,
    extract_attendees,
    extract_decisions,
    parse_transcript,
)

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "sample_transcript.txt"


def load_sample() -> str:
    return SAMPLE_PATH.read_text(encoding="utf-8")


def test_parse_transcript_extracts_all_speaker_lines():
    lines = parse_transcript(load_sample())
    assert len(lines) == 14
    assert lines[0].speaker == "Priya"
    assert lines[0].line_number == 1


def test_extract_attendees_preserves_first_seen_order_and_dedupes():
    lines = parse_transcript(load_sample())
    attendees = extract_attendees(lines)
    assert attendees == ["Priya", "Dev", "Marcus", "Sara"]


def test_extract_decisions_finds_expected_decisions():
    lines = parse_transcript(load_sample())
    decisions = extract_decisions(lines)
    descriptions = " ".join(d.description.lower() for d in decisions)
    assert len(decisions) >= 3
    assert "enterprise accounts" in descriptions
    assert "mobile redesign" in descriptions
    assert "looping in support" in descriptions


def test_extract_action_items_finds_owners_and_due_dates():
    lines = parse_transcript(load_sample())
    items = extract_action_items(lines)
    assert len(items) >= 3

    owners = {item.owner for item in items if item.owner}
    assert "Dev" in owners
    assert "Sara" in owners

    due_dates = [item.due_date for item in items if item.due_date]
    assert any("friday" in d.lower() for d in due_dates)
    assert any("wednesday" in d.lower() for d in due_dates)


def test_build_meeting_notes_end_to_end_structure():
    notes = build_meeting_notes(load_sample(), title="Q3 Planning Sync")

    assert notes.title == "Q3 Planning Sync"
    assert notes.attendees == ["Priya", "Dev", "Marcus", "Sara"]
    assert len(notes.decisions) >= 3
    assert len(notes.action_items) >= 3
    assert "Q3 Planning Sync" in notes.summary
    assert isinstance(notes.key_points, list)


def test_to_markdown_contains_all_sections():
    notes = build_meeting_notes(load_sample(), title="Q3 Planning Sync")
    md = notes.to_markdown()

    for heading in ["# Q3 Planning Sync", "## Attendees", "## Summary", "## Key Points", "## Decisions", "## Action Items"]:
        assert heading in md

    assert "Dev" in md
    assert "[ ]" in md  # action items rendered as checkboxes


def test_no_transcript_lines_produces_empty_but_valid_notes():
    notes = build_meeting_notes("just some free text with no speaker labels", title="Empty")
    assert notes.attendees == []
    assert notes.decisions == []
    assert notes.action_items == []
    assert "Empty" in notes.summary
