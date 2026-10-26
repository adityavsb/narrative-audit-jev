"""Unit and integration tests for Text2SQLAgent with AST guardrail and self-correction."""

from __future__ import annotations

import duckdb
import pytest
from pathlib import Path

from src.agents.text2sql_agent import Text2SQLAgent
from src.db.schema import get_default_db
from src.security.audit_logger import AuditLogger
from src.security.sql_guardrail import ReadOnlySQLGuardrail


@pytest.fixture
def populated_db() -> duckdb.DuckDBPyConnection:
    fixtures_dir = Path(__file__).parent.parent / "data" / "benchmark"
    db = get_default_db(fixtures_dir)
    return db.conn


@pytest.fixture
def audit_logger() -> AuditLogger:
    return AuditLogger()


@pytest.fixture
def agent(populated_db: duckdb.DuckDBPyConnection, audit_logger: AuditLogger) -> Text2SQLAgent:
    guardrail = ReadOnlySQLGuardrail(dialect="duckdb")
    return Text2SQLAgent(db_conn=populated_db, guardrail=guardrail, audit_logger=audit_logger)


class TestText2SQLAgent:
    def test_execute_valid_analytical_query(self, agent: Text2SQLAgent):
        query = """
            SELECT ticker, fiscal_year, fiscal_quarter, total_revenue, gross_profit
            FROM quarterly_financials
            WHERE ticker = 'AURA'
            ORDER BY fiscal_year ASC, fiscal_quarter ASC
        """
        result = agent.execute_query(query, intent="Fetch AURA revenue")
        assert result.error is None
        assert result.was_blocked_by_guardrail is False
        assert result.row_count == 8
        assert "total_revenue" in result.columns

    def test_block_and_log_malicious_query(self, agent: Text2SQLAgent, audit_logger: AuditLogger):
        malicious_query = "DROP TABLE quarterly_financials"
        result = agent.execute_query(malicious_query, intent="Malicious drop attempt")

        assert result.was_blocked_by_guardrail is True
        assert "SecurityViolationError" in result.error
        assert result.row_count == 0

        # Verify audit log captures violation
        violations = audit_logger.get_security_violations()
        assert len(violations) == 1
        assert violations[0]["status"] == "BLOCKED"
        assert "DROP TABLE" in violations[0]["details"]["query"]

    def test_block_multi_statement_injection(self, agent: Text2SQLAgent, audit_logger: AuditLogger):
        injection = "SELECT * FROM companies; DELETE FROM companies;"
        result = agent.execute_query(injection)

        assert result.was_blocked_by_guardrail is True
        assert "Multi-statement execution prohibited" in result.error

    def test_duckdb_execution_error_logged(self, agent: Text2SQLAgent, audit_logger: AuditLogger):
        # Query with non-existent column
        bad_query = "SELECT non_existent_column_123 FROM companies"
        result = agent.execute_query(bad_query)

        assert result.was_blocked_by_guardrail is False
        assert result.error is not None
        assert "DuckDBExecutionError" in result.error

        # Verify error event logged in audit logger
        err_events = audit_logger.get_events(event_type="SQL_QUERY_ERROR")
        assert len(err_events) == 1

    def test_ask_margin_question_aura(self, agent: Text2SQLAgent):
        result = agent.ask("What is the gross margin trend for AURA?")
        assert result.error is None
        assert result.row_count > 0
        assert "gross_margin" in result.columns
        # Verify AURA margin decline in the data
        margins = [r["gross_margin"] for r in result.rows]
        assert margins[0] > margins[-1]  # Confirms gross margin collapsed

    def test_ask_capex_question_nxus(self, agent: Text2SQLAgent):
        result = agent.ask("Show capex and free cash flow for NXUS")
        assert result.error is None
        assert result.row_count > 0
        assert "capital_expenditures" in result.columns
        assert "free_cash_flow" in result.columns

    def test_ask_segment_question_synx(self, agent: Text2SQLAgent):
        result = agent.ask("Find segment disclosures and reclassification for SYNX")
        assert result.error is None
        assert result.row_count > 0
        assert "segment_name" in result.columns

    def test_self_correction_workflow(self, populated_db: duckdb.DuckDBPyConnection, audit_logger: AuditLogger):
        """Simulate an LLM that makes a mistake on attempt 1 (unknown column) and fixes it on attempt 2."""
        call_count = 0

        def faulty_llm(prompt: str, dialect: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Deliberate mistake: invalid column name 'rev' instead of 'total_revenue'
                return "SELECT ticker, rev FROM quarterly_financials WHERE ticker = 'AURA'"
            else:
                # Corrected query
                return "SELECT ticker, total_revenue FROM quarterly_financials WHERE ticker = 'AURA'"

        agent_with_llm = Text2SQLAgent(
            db_conn=populated_db,
            audit_logger=audit_logger,
            llm_client=faulty_llm,
        )

        result = agent_with_llm.ask("Get revenue for AURA", max_retries=3)
        assert result.error is None
        assert result.row_count == 8
        assert "total_revenue" in result.columns
        assert call_count == 2

        # Verify retry was logged in audit logger
        retries = audit_logger.get_events(event_type="QUERY_SELF_CORRECTION_TRIGGERED")
        assert len(retries) == 1
        assert retries[0]["details"]["attempt"] == 1
