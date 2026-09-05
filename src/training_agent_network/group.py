"""An append-only shared group that makes coordination observable."""

from __future__ import annotations

from typing import Any

from .messages import GroupMessage, MessageType


class SharedGroup:
    """Membership and message log for one bounded task group.

    The group does not decide who should work.  It only provides a shared,
    auditable communication surface; routing remains a replaceable policy.
    """

    def __init__(self, group_id: str):
        self.group_id = group_id
        self._members: set[str] = set()
        self._messages: list[GroupMessage] = []

    @property
    def members(self) -> frozenset[str]:
        return frozenset(self._members)

    @property
    def messages(self) -> tuple[GroupMessage, ...]:
        return tuple(self._messages)

    def join(self, member_id: str, *, role: str, capabilities: list[str]) -> None:
        if member_id in self._members:
            return
        self._members.add(member_id)
        self.emit(
            MessageType.AGENT_JOINED,
            sender_id=member_id,
            payload={"role": role, "capabilities": sorted(capabilities)},
        )

    def emit(
        self,
        message_type: MessageType,
        *,
        sender_id: str,
        task_id: str | None = None,
        recipient_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> GroupMessage:
        if sender_id not in self._members:
            raise ValueError(f"sender {sender_id!r} is not a member of {self.group_id!r}")
        if recipient_id is not None and recipient_id not in self._members:
            raise ValueError(f"recipient {recipient_id!r} is not a member of {self.group_id!r}")
        message = GroupMessage(
            sequence=len(self._messages) + 1,
            group_id=self.group_id,
            message_type=message_type,
            sender_id=sender_id,
            task_id=task_id,
            recipient_id=recipient_id,
            payload=dict(payload or {}),
        )
        self._messages.append(message)
        return message

    def for_task(self, task_id: str) -> tuple[GroupMessage, ...]:
        return tuple(message for message in self._messages if message.task_id == task_id)

    def export(self) -> list[dict[str, Any]]:
        return [message.to_dict() for message in self._messages]

