"""Structured collaboration messages used by the shared group runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Minimal protocol vocabulary for forming and closing collaboration."""

    AGENT_JOINED = "agent_joined"
    TASK_POSTED = "task_posted"
    PROPOSAL = "proposal"
    COMMITMENT = "commitment"
    DELEGATION = "delegation"
    RESULT = "result"
    VERIFICATION = "verification"


@dataclass(frozen=True)
class GroupMessage:
    sequence: int
    group_id: str
    message_type: MessageType
    sender_id: str
    task_id: str | None = None
    recipient_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["message_type"] = self.message_type.value
        return value

