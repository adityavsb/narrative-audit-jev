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
from src.evaluators.openrouter_decider import OpenRouterDecisionEvaluator, load_openrouter_env


class JevDecisionEvaluator:
    """TypeSafe Jev & Multi-Model evaluator with local fallback."""

    def __init__(
        self,
        db_or_conn: Union[FinancialDatabase, duckdb.DuckDBPyConnection],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("JEV_API_KEY")
        self.model = model
        self.local_evaluator = LocalDecisionEvaluator(db_or_conn)

        # If model is specified and OpenRouter key is set, configure external decider
        self.openrouter_evaluator: Optional[OpenRouterDecisionEvaluator] = None
        env_cfg = load_openrouter_env()
        active_key = self.api_key or env_cfg.get("OPENROUTER_API_KEY")
        if self.model and active_key and not active_key.startswith("PASTE_YOUR_"):
            self.openrouter_evaluator = OpenRouterDecisionEvaluator(
                db_or_conn=db_or_conn,
                model=self.model,
                api_key=active_key,
            )

    def evaluate(
        self,
        ticker: str,
        fiscal_year: int,
        fiscal_quarter: str,
        claim_text: str,
        case_id: str = "eval",
    ) -> AuditVerdict:
        """Evaluate a claim using external model if available, or fall back to local evaluator."""
        if self.openrouter_evaluator is not None:
            return self.openrouter_evaluator.evaluate(
                ticker=ticker,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                claim_text=claim_text,
                case_id=case_id,
            )

        # Default local execution
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
