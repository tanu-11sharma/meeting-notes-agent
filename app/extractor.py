"""Rule-based meeting transcript -> structured notes extractor.

This module implements the core "agent" logic as a small, deterministic
pipeline of stages (parse -> classify -> summarize) so that it runs fully
offline on synthetic transcripts with no external API key required.

The `Summarizer` protocol at the bottom is intentionally pluggable: swapping
`HeuristicSummarizer` for an LLM-backed implementation (e.g. a call to an
LLM API) is a one-line change, which mirrors how a lot of real "agentic"
pipelines are structured in production -- a deterministic core with an
optional LLM step bolted on.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Protocol

from app.models import ActionItem, Decision, MeetingNotes

SPEAKER_LINE_RE = re.compile(r"^(?:\[[^\]]+\]\s*)?([A-Z][A-Za-z .'-]{1,30}):\s*(.+)$")

DECISION_PATTERNS = [
    r"\bwe(?:'ve| have)? decided\b",
    r"\bdecided to\b",
    r"\bagreed to\b",
    r"\bwe(?:'ll| will) go with\b",
    r"\blet's go with\b",
    r"\bfinal decision\b",
    r"\bwe're moving forward with\b",
]
DECISION_RE = re.compile("|".join(DECISION_PATTERNS), re.IGNORECASE)

ACTION_PATTERNS = [
    r"\baction item\b",
    r"\bto[- ]do\b",
    r"\bfollow up\b",
    r"\bwill\b",
    r"\bneeds? to\b",
    r"\bto (?:send|write|schedule|update|review|prepare|share|finalize|create|fix|investigate)\b",
]
ACTION_RE = re.compile("|".join(ACTION_PATTERNS), re.IGNORECASE)

OWNER_PREFIX_RE = re.compile(r"^([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?) (?:to|will|needs to)\b")

DUE_DATE_RE = re.compile(
    r"\bby (?:end of )?(?:next )?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|eod|eow|"
    r"today|tomorrow|next week|[A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?)",
    re.IGNORECASE,
)

FILLER_STARTS = ("ok", "okay", "alright", "hi", "hello", "thanks", "thank you", "sounds good", "great")


@dataclass
class TranscriptLine:
    line_number: int
    speaker: str
    text: str


def parse_transcript(raw_text: str) -> List[TranscriptLine]:
    """Parse a `Speaker: message` (optionally timestamped) transcript into lines."""
    lines: List[TranscriptLine] = []
    for i, raw_line in enumerate(raw_text.splitlines(), start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        match = SPEAKER_LINE_RE.match(raw_line)
        if not match:
            continue
        speaker, text = match.group(1).strip(), match.group(2).strip()
        lines.append(TranscriptLine(line_number=i, speaker=speaker, text=text))
    return lines


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|;\s*", text)
    return [p.strip() for p in parts if p.strip()]


def extract_attendees(lines: List[TranscriptLine]) -> List[str]:
    seen: List[str] = []
    for line in lines:
        if line.speaker not in seen:
            seen.append(line.speaker)
    return seen


def extract_decisions(lines: List[TranscriptLine]) -> List[Decision]:
    decisions: List[Decision] = []
    for line in lines:
        for sentence in _split_sentences(line.text):
            if DECISION_RE.search(sentence):
                decisions.append(Decision(description=sentence, source_line=line.line_number))
    return decisions


def _extract_due_date(sentence: str) -> Optional[str]:
    match = DUE_DATE_RE.search(sentence)
    return match.group(0) if match else None


def _extract_owner(sentence: str, speaker: str) -> Optional[str]:
    match = OWNER_PREFIX_RE.match(sentence)
    if match:
        return match.group(1)
    if re.search(r"\bI(?:'ll| will)\b", sentence):
        return speaker
    return None


def extract_action_items(lines: List[TranscriptLine]) -> List[ActionItem]:
    items: List[ActionItem] = []
    for line in lines:
        for sentence in _split_sentences(line.text):
            if DECISION_RE.search(sentence):
                continue  # a decision, not a task
            if ACTION_RE.search(sentence):
                items.append(
                    ActionItem(
                        owner=_extract_owner(sentence, line.speaker),
                        task=sentence,
                        due_date=_extract_due_date(sentence),
                        source_line=line.line_number,
                    )
                )
    return items


def extract_key_points(
    lines: List[TranscriptLine], decisions: List[Decision], action_items: List[ActionItem], limit: int = 5
) -> List[str]:
    used_line_numbers = {d.source_line for d in decisions} | {a.source_line for a in action_items}
    candidates: List[str] = []
    for line in lines:
        if line.line_number in used_line_numbers:
            continue
        for sentence in _split_sentences(line.text):
            lowered = sentence.lower()
            if len(sentence.split()) < 6:
                continue
            if lowered.startswith(FILLER_STARTS):
                continue
            candidates.append(sentence)
    # Rank by length (proxy for informativeness) and keep original order among ties.
    candidates.sort(key=len, reverse=True)
    return candidates[:limit]


class Summarizer(Protocol):
    def summarize(
        self,
        title: str,
        attendees: List[str],
        decisions: List[Decision],
        action_items: List[ActionItem],
    ) -> str:
        ...


class HeuristicSummarizer:
    """Deterministic, template-based summary. No external API calls."""

    def summarize(
        self,
        title: str,
        attendees: List[str],
        decisions: List[Decision],
        action_items: List[ActionItem],
    ) -> str:
        attendee_clause = (
            f"with {len(attendees)} participant(s) ({', '.join(attendees)})"
            if attendees
            else "with no identifiable participants"
        )
        decision_clause = (
            f"{len(decisions)} decision(s) were made"
            if decisions
            else "no explicit decisions were recorded"
        )
        action_clause = (
            f"{len(action_items)} action item(s) were assigned"
            if action_items
            else "no action items were identified"
        )
        return f"\"{title}\" {attendee_clause}. During the discussion, {decision_clause} and {action_clause}."


def build_meeting_notes(
    raw_transcript: str,
    title: str = "Meeting Notes",
    summarizer: Optional[Summarizer] = None,
) -> MeetingNotes:
    summarizer = summarizer or HeuristicSummarizer()
    lines = parse_transcript(raw_transcript)
    attendees = extract_attendees(lines)
    decisions = extract_decisions(lines)
    action_items = extract_action_items(lines)
    key_points = extract_key_points(lines, decisions, action_items)
    summary = summarizer.summarize(title, attendees, decisions, action_items)
    return MeetingNotes(
        title=title,
        attendees=attendees,
        summary=summary,
        key_points=key_points,
        decisions=decisions,
        action_items=action_items,
    )
