"""Typed data schemas and Pydantic models for multi-step agent execution."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DivergenceType(str, Enum):
    MARGIN_DILUTION = "MARGIN_DILUTION"
    CAPITAL_SINKHOLE = "CAPITAL_SINKHOLE"
    REVENUE_RECLASSIFICATION = "REVENUE_RECLASSIFICATION"
    PILOT_CHURN = "PILOT_CHURN"
    NONE = "NONE"


class MaterialityTier(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SQLToolCall(BaseModel):
    """Specification of an analytical SQL execution request."""
    query: str = Field(description="SQL query string to execute against DuckDB")
    intent: str = Field(default="", description="Natural language reasoning or intent behind query")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp of query dispatch")


class SQLToolResult(BaseModel):
    """Result returned by DuckDB execution after passing AST guardrail."""
    query: str
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    was_blocked_by_guardrail: bool = False


class ClaimExtraction(BaseModel):
    """Structured extraction of an executive qualitative assertion from transcripts."""
    claim_id: str = Field(description="Unique identifier for the qualitative claim")
    ticker: str
    fiscal_year: int
    fiscal_quarter: str
    speaker_name: str
    speaker_title: str
    statement: str = Field(description="Verbatim or summarized executive assertion")
    claim_type: str = Field(description="e.g., 'gross_margin', 'capex_efficiency', 'ai_arr', 'customer_adoption'")
    metrics_mentioned: List[str] = Field(default_factory=list)
    sentiment_direction: str = Field(default="EXPANSION", description="'EXPANSION', 'CONTRACTION', 'STABLE', or 'NEUTRAL'")


class NumericFactCheck(BaseModel):
    """Verification result reconciling a claimed numerical value against audited accounting rows."""
    metric: str
    claimed_value: Optional[float] = None
    audited_value: Optional[float] = None
    delta_percent: Optional[float] = None
    is_verified: bool = False
    tolerance_threshold: float = 0.01  # Default 1% tolerance
    explanation: str = Field(description="Detailed reconciling rationale between statement and ledger")


class AuditVerdict(BaseModel):
    """Final executive audit verdict delivered for a company-quarter."""
    ticker: str
    fiscal_year: int
    fiscal_quarter: str
    is_discrepancy: bool
    divergence_type: DivergenceType
    materiality: MaterialityTier
    ndi_score: float = Field(ge=0.0, le=100.0, description="Narrative Divergence Index (0-100)")
    confidence: float = Field(ge=0.0, le=1.0, description="Calibrated confidence P(Divergence)")
    summary: str
    supporting_evidence: List[str] = Field(default_factory=list)
    fact_checks: List[NumericFactCheck] = Field(default_factory=list)
    audit_trail_ids: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Complete multi-turn state container for the financial audit agent."""
    session_id: str
    ticker: str
    fiscal_year: int
    fiscal_quarter: str
    current_step: str = "INITIALIZED"
    retries_remaining: int = 3
    tool_calls: List[SQLToolCall] = Field(default_factory=list)
    tool_results: List[SQLToolResult] = Field(default_factory=list)
    extracted_claims: List[ClaimExtraction] = Field(default_factory=list)
    fact_checks: List[NumericFactCheck] = Field(default_factory=list)
    final_verdict: Optional[AuditVerdict] = None
    errors: List[str] = Field(default_factory=list)
