"""Unit tests for Structured Immutable Audit Logger."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from src.security.audit_logger import AuditLogger, get_audit_logger


class TestAuditLogger:
    def test_in_memory_logging(self):
        logger = AuditLogger()
        event = logger.log_event(
            event_type="SQL_QUERY",
            agent_id="text2sql_agent",
            status="SUCCESS",
            details={"query": "SELECT 1", "rows": 1},
            execution_time_ms=12.4,
        )

        assert event["status"] == "SUCCESS"
        assert event["agent_id"] == "text2sql_agent"
        assert event["execution_time_ms"] == 12.4
        assert len(logger.get_events()) == 1

    def test_file_persistence(self, tmp_path: Path):
        log_file = tmp_path / "test_audit.jsonl"
        logger = AuditLogger(log_file=log_file)

        logger.log_event(
            event_type="SQL_QUERY",
            agent_id="text2sql_agent",
            status="SUCCESS",
            details={"query": "SELECT * FROM companies"},
            execution_time_ms=4.5,
        )
        logger.log_event(
            event_type="SECURITY_VIOLATION",
            agent_id="sql_guardrail",
            status="BLOCKED",
            details={"violation": "DROP TABLE blocked"},
            execution_time_ms=1.1,
        )

        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

        entry0 = json.loads(lines[0])
        assert entry0["event_type"] == "SQL_QUERY"
        assert entry0["status"] == "SUCCESS"

        entry1 = json.loads(lines[1])
        assert entry1["event_type"] == "SECURITY_VIOLATION"
        assert entry1["status"] == "BLOCKED"

    def test_filtering_and_violations(self):
        logger = AuditLogger()
        logger.log_event("TOOL_CALL", "agent_1", "SUCCESS", {"tool": "duckdb"})
        logger.log_event("SECURITY_VIOLATION", "guardrail", "BLOCKED", {"reason": "Injection"})
        logger.log_event("TOOL_CALL", "agent_2", "SUCCESS", {"tool": "duckdb"})

        assert len(logger.get_events(event_type="TOOL_CALL")) == 2
        assert len(logger.get_events(agent_id="agent_1")) == 1
        assert len(logger.get_security_violations()) == 1

    def test_clear_logs(self):
        logger = AuditLogger()
        logger.log_event("TOOL_CALL", "agent_1", "SUCCESS", {})
        assert len(logger.get_events()) == 1
        logger.clear()
        assert len(logger.get_events()) == 0
