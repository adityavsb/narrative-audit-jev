"""Text2SQL helper with read-only AST guard and optional LLM client hook."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
import duckdb

from src.agents.state import SQLToolCall, SQLToolResult
from src.security.audit_logger import AuditLogger, get_audit_logger
from src.security.sql_guardrail import ReadOnlySQLGuardrail, SecurityViolationError


SCHEMA_CONTEXT = """
DuckDB Financial Database Schema:

Table `companies`:
  - ticker VARCHAR PRIMARY KEY
  - name VARCHAR NOT NULL
  - sector VARCHAR NOT NULL
  - business_model VARCHAR
  - fiscal_year_end VARCHAR
  - currency VARCHAR
  - is_control_baseline BOOLEAN

Table `quarterly_financials`:
  - ticker VARCHAR REFERENCES companies(ticker)
  - fiscal_year INTEGER NOT NULL
  - fiscal_quarter VARCHAR NOT NULL (e.g. 'Q1', 'Q2', 'Q3', 'Q4')
  - period_end_date DATE NOT NULL
  - total_revenue DOUBLE
  - cost_of_goods_sold DOUBLE
  - gross_profit DOUBLE (total_revenue - cost_of_goods_sold)
  - operating_income DOUBLE
  - net_income DOUBLE
  - operating_cash_flow DOUBLE
  - capital_expenditures DOUBLE
  - free_cash_flow DOUBLE (operating_cash_flow - capital_expenditures)
  - cash_and_equivalents DOUBLE
  - deferred_revenue DOUBLE

Table `segment_disclosures`:
  - ticker VARCHAR REFERENCES companies(ticker)
  - fiscal_year INTEGER NOT NULL
  - fiscal_quarter VARCHAR NOT NULL
  - segment_name VARCHAR NOT NULL
  - segment_revenue DOUBLE
  - segment_gross_margin DOUBLE
  - is_reported_organic BOOLEAN
  - notes VARCHAR

Table `transcripts`:
  - ticker VARCHAR REFERENCES companies(ticker)
  - fiscal_year INTEGER NOT NULL
  - fiscal_quarter VARCHAR NOT NULL
  - section VARCHAR ('PREPARED_REMARKS' or 'ANALYST_QA')
  - speaker_name VARCHAR
  - speaker_title VARCHAR
  - content VARCHAR
  - sequence_order INTEGER
"""


class Text2SQLAgent:
    """Runs SQL through ReadOnlySQLGuardrail; supports heuristic or LLM-generated queries."""

    def __init__(
        self,
        db_conn: duckdb.DuckDBPyConnection,
        guardrail: Optional[ReadOnlySQLGuardrail] = None,
        audit_logger: Optional[AuditLogger] = None,
        llm_client: Optional[Callable[[str, str], str]] = None,
    ):
        self.conn = db_conn
        self.guardrail = guardrail or ReadOnlySQLGuardrail(dialect="duckdb")
        self.audit_logger = audit_logger or get_audit_logger()
        self.llm_client = llm_client

    def execute_query(self, query: str, intent: str = "") -> SQLToolResult:
        """Validate via AST guardrail, log to audit trail, and execute against DuckDB."""
        t0 = time.perf_counter()

        # Step 1: Validate AST and check for prohibited expressions
        try:
            sanitized_sql = self.guardrail.validate_and_sanitize(query)
        except SecurityViolationError as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.audit_logger.log_event(
                event_type="SECURITY_VIOLATION",
                agent_id="text2sql_agent",
                status="BLOCKED",
                details={"query": query, "intent": intent, "reason": str(e)},
                execution_time_ms=elapsed_ms,
            )
            return SQLToolResult(
                query=query,
                error=f"SecurityViolationError: {str(e)}",
                was_blocked_by_guardrail=True,
                execution_time_ms=elapsed_ms,
            )

        # Step 2: Execute sanitized query against DuckDB
        try:
            df = self.conn.execute(sanitized_sql).df()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            rows = df.to_dict(orient="records")
            columns = list(df.columns)

            self.audit_logger.log_event(
                event_type="SQL_QUERY_SUCCESS",
                agent_id="text2sql_agent",
                status="SUCCESS",
                details={
                    "query": sanitized_sql,
                    "intent": intent,
                    "row_count": len(rows),
                    "columns": columns,
                },
                execution_time_ms=elapsed_ms,
            )

            return SQLToolResult(
                query=sanitized_sql,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=elapsed_ms,
                error=None,
                was_blocked_by_guardrail=False,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.audit_logger.log_event(
                event_type="SQL_QUERY_ERROR",
                agent_id="text2sql_agent",
                status="FAILED",
                details={"query": sanitized_sql, "intent": intent, "error": str(e)},
                execution_time_ms=elapsed_ms,
            )
            return SQLToolResult(
                query=sanitized_sql,
                error=f"DuckDBExecutionError: {str(e)}",
                was_blocked_by_guardrail=False,
                execution_time_ms=elapsed_ms,
            )

    def generate_sql(self, question: str, previous_error: Optional[str] = None) -> str:
        """Translate natural language into SQL using LLM or rule-based semantic parser."""
        if self.llm_client:
            prompt = f"Schema:\n{SCHEMA_CONTEXT}\n\nQuestion: {question}"
            if previous_error:
                prompt += f"\n\nPrevious attempt failed with error: {previous_error}\nPlease fix the query."
            return self.llm_client(prompt, "duckdb")

        # Fallback / Built-in deterministic semantic pattern generator for offline CI
        return self._semantic_parser(question, previous_error)

    def _semantic_parser(self, question: str, previous_error: Optional[str] = None) -> str:
        """Deterministic semantic parser for benchmark auditing questions."""
        q_lower = question.lower()

        # Handle self-correction if column error occurred
        if previous_error and "revenue" in previous_error.lower() and "rev" in previous_error.lower():
            # e.g., user had used 'rev' instead of 'total_revenue'
            return "SELECT ticker, fiscal_year, fiscal_quarter, total_revenue FROM quarterly_financials ORDER BY fiscal_year, fiscal_quarter"

        # Detect ticker
        ticker = None
        for t in ["AURA", "NXUS", "SYNX", "VORS"]:
            if t.lower() in q_lower:
                ticker = t
                break

        # 1. Gross margin trends / dilution
        if "gross margin" in q_lower or "margin" in q_lower or "dilution" in q_lower:
            where_clause = f"WHERE ticker = '{ticker}'" if ticker else ""
            return f"""
                SELECT ticker, fiscal_year, fiscal_quarter, total_revenue, cost_of_goods_sold, gross_profit,
                       ROUND(gross_profit / NULLIF(total_revenue, 0), 4) as gross_margin
                FROM quarterly_financials
                {where_clause}
                ORDER BY fiscal_year ASC, fiscal_quarter ASC
            """.strip()

        # 2. Capex and Free Cash Flow sinkhole
        if "capex" in q_lower or "free cash flow" in q_lower or "fcf" in q_lower:
            where_clause = f"WHERE ticker = '{ticker}'" if ticker else ""
            return f"""
                SELECT ticker, fiscal_year, fiscal_quarter, total_revenue, operating_cash_flow,
                       capital_expenditures, free_cash_flow,
                       ROUND(capital_expenditures / NULLIF(total_revenue, 0), 4) as capex_intensity
                FROM quarterly_financials
                {where_clause}
                ORDER BY fiscal_year ASC, fiscal_quarter ASC
            """.strip()

        # 3. Segment disclosures and reclassification
        if "segment" in q_lower or "arr" in q_lower or "reclassification" in q_lower:
            where_clause = f"WHERE ticker = '{ticker}'" if ticker else ""
            return f"""
                SELECT ticker, fiscal_year, fiscal_quarter, segment_name, segment_revenue,
                       segment_gross_margin, is_reported_organic, notes
                FROM segment_disclosures
                {where_clause}
                ORDER BY fiscal_year ASC, fiscal_quarter ASC
            """.strip()

        # 4. Transcripts
        if "transcript" in q_lower or "speaker" in q_lower or "quote" in q_lower or "said" in q_lower:
            where_clause = f"WHERE ticker = '{ticker}'" if ticker else ""
            return f"""
                SELECT ticker, fiscal_year, fiscal_quarter, section, speaker_name, speaker_title, content
                FROM transcripts
                {where_clause}
                ORDER BY fiscal_year DESC, fiscal_quarter DESC, sequence_order ASC
            """.strip()

        # Default fallback
        where_clause = f"WHERE ticker = '{ticker}'" if ticker else ""
        return f"SELECT * FROM quarterly_financials {where_clause} ORDER BY fiscal_year ASC, fiscal_quarter ASC"

    def ask(self, question: str, max_retries: int = 3) -> SQLToolResult:
        """Full Text2SQL workflow with autonomous self-correction loop."""
        previous_error = None
        last_result: Optional[SQLToolResult] = None

        for attempt in range(1, max_retries + 1):
            query = self.generate_sql(question, previous_error=previous_error)
            intent = f"Attempt {attempt}/{max_retries} for query: {question}"

            result = self.execute_query(query, intent=intent)
            last_result = result

            if result.error is None:
                return result

            # If blocked by guardrail or execution error, retry
            previous_error = result.error
            self.audit_logger.log_event(
                event_type="QUERY_SELF_CORRECTION_TRIGGERED",
                agent_id="text2sql_agent",
                status="RETRYING",
                details={
                    "attempt": attempt,
                    "max_retries": max_retries,
                    "failed_query": query,
                    "error": result.error,
                },
            )

        assert last_result is not None
        return last_result
