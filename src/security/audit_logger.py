"""Structured audit logger for multi-agent execution, tool calls, and security events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditLogger:
    """Append-only JSONL audit trail when a log file path is configured."""

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self.in_memory_logs: List[Dict[str, Any]] = []

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        agent_id: str,
        status: str,
        details: Dict[str, Any],
        execution_time_ms: float = 0.0,
    ) -> Dict[str, Any]:
        """Record an immutable audit event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "status": status,
            "execution_time_ms": round(execution_time_ms, 2),
            "details": details,
        }

        self.in_memory_logs.append(entry)

        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

        return entry

    def get_events(self, event_type: Optional[str] = None, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filter audit events."""
        filtered = self.in_memory_logs
        if event_type:
            filtered = [e for e in filtered if e["event_type"] == event_type]
        if agent_id:
            filtered = [e for e in filtered if e["agent_id"] == agent_id]
        return filtered

    def get_security_violations(self) -> List[Dict[str, Any]]:
        """Retrieve all security-blocked events."""
        return [e for e in self.in_memory_logs if e["status"] == "BLOCKED"]

    def clear(self) -> None:
        """Clear in-memory logs (used in test fixtures)."""
        self.in_memory_logs.clear()


# Default global audit logger instance
_default_logger = AuditLogger()


def get_audit_logger(log_file: Optional[Path] = None) -> AuditLogger:
    """Factory to get configured audit logger."""
    if log_file:
        return AuditLogger(log_file=log_file)
    return _default_logger
