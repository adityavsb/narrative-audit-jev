"""Unit tests for AST-enforced Read-Only SQL Guardrail."""

from __future__ import annotations

import pytest
from src.security.sql_guardrail import ReadOnlySQLGuardrail, SecurityViolationError


@pytest.fixture
def guardrail() -> ReadOnlySQLGuardrail:
    return ReadOnlySQLGuardrail(dialect="duckdb")


class TestReadOnlySQLGuardrail:
    def test_valid_simple_select(self, guardrail: ReadOnlySQLGuardrail):
        query = "SELECT ticker, total_revenue FROM quarterly_financials WHERE fiscal_year = 2024"
        clean = guardrail.validate_and_sanitize(query)
        assert "SELECT" in clean
        assert "quarterly_financials" in clean
        assert guardrail.is_safe(query) is True

    def test_valid_cte_select(self, guardrail: ReadOnlySQLGuardrail):
        query = """
        WITH yearly_rev AS (
            SELECT ticker, fiscal_year, SUM(total_revenue) as annual_rev
            FROM quarterly_financials
            GROUP BY ticker, fiscal_year
        )
        SELECT ticker, fiscal_year, annual_rev FROM yearly_rev WHERE annual_rev > 1000000
        """
        assert guardrail.is_safe(query) is True
        clean = guardrail.validate_and_sanitize(query)
        assert "WITH" in clean

    def test_valid_window_function_and_subquery(self, guardrail: ReadOnlySQLGuardrail):
        query = """
        SELECT ticker, period_end_date, gross_profit,
               LAG(gross_profit, 1) OVER (PARTITION BY ticker ORDER BY period_end_date) as prev_gp
        FROM quarterly_financials
        WHERE ticker IN (SELECT ticker FROM companies WHERE sector = 'Enterprise Software')
        """
        assert guardrail.is_safe(query) is True

    def test_valid_union_query(self, guardrail: ReadOnlySQLGuardrail):
        query = """
        SELECT ticker, total_revenue FROM quarterly_financials WHERE fiscal_year = 2023
        UNION ALL
        SELECT ticker, total_revenue FROM quarterly_financials WHERE fiscal_year = 2024
        """
        assert guardrail.is_safe(query) is True

    def test_block_empty_or_whitespace_query(self, guardrail: ReadOnlySQLGuardrail):
        with pytest.raises(SecurityViolationError, match="Empty SQL query"):
            guardrail.validate_and_sanitize("   ")
        assert guardrail.is_safe("") is False

    def test_block_drop_table(self, guardrail: ReadOnlySQLGuardrail):
        query = "DROP TABLE companies"
        with pytest.raises(SecurityViolationError, match="Only read-only SELECT or UNION queries permitted"):
            guardrail.validate_and_sanitize(query)
        assert guardrail.is_safe(query) is False

    def test_block_delete_statement(self, guardrail: ReadOnlySQLGuardrail):
        query = "DELETE FROM quarterly_financials WHERE ticker = 'AURA'"
        with pytest.raises(SecurityViolationError):
            guardrail.validate_and_sanitize(query)
        assert guardrail.is_safe(query) is False

    def test_block_insert_statement(self, guardrail: ReadOnlySQLGuardrail):
        query = "INSERT INTO companies (ticker, name) VALUES ('HACK', 'Malicious Corp')"
        with pytest.raises(SecurityViolationError):
            guardrail.validate_and_sanitize(query)
        assert guardrail.is_safe(query) is False

    def test_block_update_statement(self, guardrail: ReadOnlySQLGuardrail):
        query = "UPDATE quarterly_financials SET total_revenue = 999999999 WHERE ticker = 'AURA'"
        with pytest.raises(SecurityViolationError):
            guardrail.validate_and_sanitize(query)
        assert guardrail.is_safe(query) is False

    def test_block_multi_statement_injection(self, guardrail: ReadOnlySQLGuardrail):
        query = "SELECT * FROM companies; DROP TABLE quarterly_financials;"
        with pytest.raises(SecurityViolationError, match="Multi-statement execution prohibited"):
            guardrail.validate_and_sanitize(query)
        assert guardrail.is_safe(query) is False

    def test_block_prohibited_filesystem_functions(self, guardrail: ReadOnlySQLGuardrail):
        dangerous_queries = [
            "SELECT * FROM read_csv('/etc/passwd')",
            "SELECT * FROM read_parquet('s3://internal-bucket/data.parquet')",
            "SELECT * FROM read_json('/root/.aws/credentials')",
            "COPY quarterly_financials TO '/tmp/dump.csv'",
        ]
        for q in dangerous_queries:
            assert guardrail.is_safe(q) is False, f"Expected {q} to be blocked"
            with pytest.raises(SecurityViolationError):
                guardrail.validate_and_sanitize(q)

    def test_block_syntax_error(self, guardrail: ReadOnlySQLGuardrail):
        query = "SELECT FROM WHERE GROUP"
        with pytest.raises(SecurityViolationError, match="SQL Syntax parsing failed"):
            guardrail.validate_and_sanitize(query)
        assert guardrail.is_safe(query) is False
