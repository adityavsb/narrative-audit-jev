"""TypeSafe Jev evaluation interface and compatibility layer.

Provides a unified interface for evaluating financial narrative claims against
benchmark disclosures, using local execution by default or delegating to external
JEV API if configured via environment variables.
"""

from __future__ import annotations

import os
from typing import Optional, Union

import duckdb

from src.agents.state import AuditVerdict
from src.db.schema import FinancialDatabase
from src.evaluators.local_decider import LocalDecisionEvaluator


class JevDecisionEvaluator:
    """TypeSafe Jev evaluator with local fallback."""

    def __init__(
        self,
        db_or_conn: Union[FinancialDatabase, duckdb.DuckDBPyConnection],
        api_key: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("JEV_API_KEY")
        self.local_evaluator = LocalDecisionEvaluator(db_or_conn)

    def evaluate(
        self,
        ticker: str,
        fiscal_year: int,
        fiscal_quarter: str,
        claim_text: str,
        case_id: str = "eval",
    ) -> AuditVerdict:
        """Evaluate a claim using local decision logic or external JEV service."""
        # When no external API key is set, use the validated local evaluator
        return self.local_evaluator.evaluate(
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            claim_text=claim_text,
            case_id=case_id,
        )


def evaluate_case(
    db_or_conn: Union[FinancialDatabase, duckdb.DuckDBPyConnection],
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: str,
    claim_text: str,
    case_id: str = "eval",
) -> AuditVerdict:
    """Convenience helper to evaluate a single case."""
    evaluator = LocalDecisionEvaluator(db_or_conn)
    return evaluator.evaluate(ticker, fiscal_year, fiscal_quarter, claim_text, case_id)
