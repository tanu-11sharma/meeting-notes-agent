"""Pydantic data models for structured meeting notes output."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ActionItem(BaseModel):
    owner: Optional[str] = Field(
        None, description="Person responsible for the task, if one could be identified"
    )
    task: str = Field(..., description="The action to be taken")
    due_date: Optional[str] = Field(
        None, description="Due date exactly as mentioned in the transcript, if any"
    )
    source_line: int = Field(..., description="Transcript line number this was extracted from")


class Decision(BaseModel):
    description: str = Field(..., description="The decision that was made")
    source_line: int = Field(..., description="Transcript line number this was extracted from")


class MeetingNotes(BaseModel):
    title: str
    attendees: List[str]
    summary: str
    key_points: List[str]
    decisions: List[Decision]
    action_items: List[ActionItem]

    def to_markdown(self) -> str:
        lines: List[str] = [f"# {self.title}", ""]
        lines.append("## Attendees")
        lines.append(", ".join(self.attendees) if self.attendees else "_None identified_")
        lines.append("")
        lines.append("## Summary")
        lines.append(self.summary)
        lines.append("")
        lines.append("## Key Points")
        if self.key_points:
            lines.extend(f"- {point}" for point in self.key_points)
        else:
            lines.append("_None identified_")
        lines.append("")
        lines.append("## Decisions")
        if self.decisions:
            lines.extend(f"- {d.description} _(line {d.source_line})_" for d in self.decisions)
        else:
            lines.append("_None identified_")
        lines.append("")
        lines.append("## Action Items")
        if self.action_items:
            for item in self.action_items:
                owner = item.owner or "Unassigned"
                due = f" — due {item.due_date}" if item.due_date else ""
                lines.append(f"- [ ] **{owner}**: {item.task}{due} _(line {item.source_line})_")
        else:
            lines.append("_None identified_")
        return "\n".join(lines) + "\n"
