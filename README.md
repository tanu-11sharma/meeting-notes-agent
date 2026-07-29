# meeting-notes-agent

Turn a raw meeting transcript into structured notes: attendees, a summary, key
points, decisions, and action items (with owner + due date extracted where
possible) — as clean Markdown or JSON.

## Why this is relevant

"Meeting transcript → structured notes + action items" is one of the most
common real-world agentic AI patterns being shipped right now: a small
pipeline of parse → classify → summarize stages that turns messy unstructured
text into a structured, actionable artifact. This project implements that
pipeline end-to-end with a **deterministic, rule-based core** (regex +
heuristics, no LLM API key required to run the demo), while keeping the
summarization step behind a `Summarizer` protocol — so swapping in an
LLM-backed summarizer later is a one-line change. That "deterministic core
with a pluggable AI step" shape is exactly how a lot of production agent
pipelines are actually structured.

This is a demo built on a synthetic sample transcript. It does not call any
external service and does not process real meeting recordings or real
personal data.

## What it does

Given a transcript file where each line looks like `Speaker: message`
(an optional `[timestamp]` prefix is supported), it extracts:

- **Attendees** — unique speakers, in order of first appearance
- **Decisions** — sentences matching decision language ("we decided...",
  "agreed to...", "let's go with...")
- **Action items** — sentences matching task language ("I'll...", "X to
  do Y by Friday...", "action item...", "follow up..."), with best-effort
  owner and due-date extraction
- **Key points** — other substantive sentences not already captured above
- **Summary** — a short templated summary of attendee/decision/action counts

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
# Markdown output (default)
python -m app.cli sample_data/sample_transcript.txt --title "Q3 Planning Sync"

# JSON output
python -m app.cli sample_data/sample_transcript.txt --title "Q3 Planning Sync" --format json
```

Example Markdown output (truncated):

```markdown
# Q3 Planning Sync

## Attendees
Priya, Dev, Marcus, Sara

## Summary
"Q3 Planning Sync" with 4 participant(s) (Priya, Dev, Marcus, Sara). During
the discussion, 3 decision(s) were made and 4 action item(s) were assigned.

## Action Items
- [ ] **Dev**: I'll pull together the churn data... — due by Friday _(line 2)_
- [ ] **Sara**: Sara to send the survey draft by Wednesday... _(line 5)_
```

### Docker

```bash
docker build -t meeting-notes-agent .
docker run --rm meeting-notes-agent
```

## Test

```bash
pytest -q
```

7 tests cover transcript parsing, attendee de-duplication, decision
detection, action-item owner/due-date extraction, end-to-end note building,
Markdown rendering, and the empty-transcript edge case.

## Project layout

```
app/
  models.py     # Pydantic models: ActionItem, Decision, MeetingNotes
  extractor.py  # parse -> classify -> summarize pipeline
  cli.py        # CLI entry point
sample_data/
  sample_transcript.txt
tests/
  test_extractor.py
```
