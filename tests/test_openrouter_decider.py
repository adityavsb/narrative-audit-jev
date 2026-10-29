"""Unit tests for OpenRouter decision evaluator, prompt sandboxing, and secret hygiene."""

import io
import json
from unittest.mock import MagicMock, patch
import pytest

from src.agents.state import AuditVerdict, DivergenceType, MaterialityTier
from src.db.schema import get_default_db
from src.evaluators.openrouter_decider import (
    OpenRouterDecisionEvaluator,
    build_audit_prompt,
    extract_json_payload,
    load_openrouter_env,
    mask_secret,
)
from src.security.leakage_verifier import LeakageVerifier


@pytest.fixture
def test_db():
    db = get_default_db()
    yield db
    db.close()


def test_mask_secret():
    assert mask_secret(None) == "[NOT SET]"
    assert mask_secret("") == "[NOT SET]"
    assert mask_secret("short") == "***MASKED***"
    assert mask_secret("sk-or-v1-1234567890abcdef") == "sk-or-...cdef"


def test_load_openrouter_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENROUTER_API_KEY=test_key_12345\n"
        "OPENROUTER_MODEL_1=test/model-1\n"
        "# comment line\n"
        "OPENROUTER_REQUEST_DELAY_SEC=0.5\n"
    )
    cfg = load_openrouter_env(env_file)
    assert cfg["OPENROUTER_API_KEY"] == "test_key_12345"
    assert cfg["OPENROUTER_MODEL_1"] == "test/model-1"
    assert cfg["OPENROUTER_REQUEST_DELAY_SEC"] == "0.5"


def test_build_audit_prompt_xml_structure(test_db):
    sys_prompt, user_prompt = build_audit_prompt(
        test_db.conn,
        ticker="AURA",
        fiscal_year=2025,
        fiscal_quarter="Q4",
        claim_text="Our gross margins remained resilient throughout generative AI rollout.",
    )

    assert "expert quantitative forensic accountant" in sys_prompt
    assert "ADVERSARIAL RESISTANCE" in sys_prompt
    assert "AuditVerdict" in sys_prompt or "is_discrepancy" in sys_prompt

    assert '<audited_financials ticker="AURA">' in user_prompt
    assert "</audited_financials>" in user_prompt
    assert '<segment_disclosures ticker="AURA">' in user_prompt
    assert "</segment_disclosures>" in user_prompt
    assert '<transcript_context ticker="AURA">' in user_prompt
    assert "</transcript_context>" in user_prompt
    assert '<claim_to_evaluate ticker="AURA"' in user_prompt
    assert "</claim_to_evaluate>" in user_prompt


def test_extract_json_payload_clean():
    raw = '{"ticker": "AURA", "is_discrepancy": true, "confidence": 0.95}'
    parsed = extract_json_payload(raw)
    assert parsed["ticker"] == "AURA"
    assert parsed["is_discrepancy"] is True


def test_extract_json_payload_markdown_fences():
    raw = (
        "Here is the evaluation result:\n\n"
        "```json\n"
        "{\n"
        '  "ticker": "NXUS",\n'
        '  "is_discrepancy": true,\n'
        '  "confidence": 0.88\n'
        "}\n"
        "```\n"
    )
    parsed = extract_json_payload(raw)
    assert parsed["ticker"] == "NXUS"
    assert parsed["is_discrepancy"] is True


def test_extract_json_payload_reasoning_tags():
    raw = (
        "<think>\n"
        "The user claims gross margins expanded, but audited Q4 2025 GM fell to 61% from 79%.\n"
        "This is an 1800 bps contraction.\n"
        "</think>\n"
        "{\n"
        '  "ticker": "AURA",\n'
        '  "fiscal_year": 2025,\n'
        '  "fiscal_quarter": "Q4",\n'
        '  "is_discrepancy": true,\n'
        '  "divergence_type": "MARGIN_DILUTION",\n'
        '  "materiality": "CRITICAL",\n'
        '  "ndi_score": 85.0,\n'
        '  "confidence": 0.92,\n'
        '  "summary": "1800 bps margin contraction contradicts resilient claim",\n'
        '  "supporting_evidence": ["audited GM fell to 61%"],\n'
        '  "fact_checks": []\n'
        "}"
    )
    parsed = extract_json_payload(raw)
    assert parsed["ticker"] == "AURA"
    assert parsed["is_discrepancy"] is True
    assert parsed["divergence_type"] == "MARGIN_DILUTION"


def test_openrouter_evaluator_unconfigured_key_error(test_db):
    evaluator = OpenRouterDecisionEvaluator(
        db_or_conn=test_db,
        model="google/gemma-4-26b-a4b-it:free",
        api_key="PASTE_YOUR_OPENROUTER_KEY_HERE",
    )
    with pytest.raises(ValueError, match="OpenRouter API key is not configured"):
        evaluator.evaluate("AURA", 2025, "Q4", "Testing claim")


def test_openrouter_evaluator_repr_does_not_leak_key(test_db):
    evaluator = OpenRouterDecisionEvaluator(
        db_or_conn=test_db,
        model="google/gemma-4-26b-a4b-it:free",
        api_key="sk-or-v1-secret1234567890abcdef",
    )
    repr_str = repr(evaluator)
    assert "sk-or-v1-secret1234567890abcdef" not in repr_str
    assert "sk-or-...cdef" in repr_str


def test_openrouter_evaluator_mocked_http_success(test_db):
    mock_response_payload = {
        "id": "gen-12345",
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "ticker": "AURA",
                        "fiscal_year": 2025,
                        "fiscal_quarter": "Q4",
                        "is_discrepancy": True,
                        "divergence_type": "MARGIN_DILUTION",
                        "materiality": "CRITICAL",
                        "ndi_score": 75.0,
                        "confidence": 0.94,
                        "summary": "Audited GM contracted by 1800 bps from 79% to 61%.",
                        "supporting_evidence": ["Gross margin fell from 79% to 61%"],
                        "fact_checks": [
                            {
                                "metric": "gross_margin",
                                "claimed_value": None,
                                "audited_value": 0.61,
                                "delta_percent": -0.2278,
                                "is_verified": False,
                                "explanation": "Contraction of 1800 bps"
                            }
                        ]
                    })
                }
            }
        ],
        "usage": {
            "prompt_tokens": 1450,
            "completion_tokens": 320,
            "total_tokens": 1770
        }
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        evaluator = OpenRouterDecisionEvaluator(
            db_or_conn=test_db,
            model="google/gemma-4-26b-a4b-it:free",
            api_key="sk-or-v1-mockedkey1234567890",
            request_delay_sec=0.0,
        )

        verdict = evaluator.evaluate(
            ticker="AURA",
            fiscal_year=2025,
            fiscal_quarter="Q4",
            claim_text="Our gross margins remained resilient.",
            case_id="AURA_001",
        )

        assert isinstance(verdict, AuditVerdict)
        assert verdict.ticker == "AURA"
        assert verdict.is_discrepancy is True
        assert verdict.divergence_type == DivergenceType.MARGIN_DILUTION
        assert verdict.materiality == MaterialityTier.CRITICAL
        assert verdict.confidence == 0.94
        assert len(verdict.fact_checks) == 1
        assert evaluator.last_telemetry["prompt_tokens"] == 1450
        assert evaluator.last_telemetry["completion_tokens"] == 320


def test_openrouter_evaluator_mocked_decisions_api_success(test_db):
    mock_decision_payload = {
        "model": "perplexity/pplx-decider-flash-v1.2",
        "answers": {
            "is_discrepancy": {
                "type": "noul",
                "noul": 0.885
            },
            "divergence_category": {
                "type": "choice",
                "choice": "MARGIN_DILUTION",
                "confidence": 0.92
            },
            "materiality": {
                "type": "choice",
                "choice": "CRITICAL",
                "confidence": 0.85
            }
        },
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 3
        }
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_decision_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        evaluator = OpenRouterDecisionEvaluator(
            db_or_conn=test_db,
            model="perplexity/pplx-decider-flash-v1.2",
            api_key="sk-or-v1-mockedkey1234567890",
            request_delay_sec=0.0,
        )

        verdict = evaluator.evaluate(
            ticker="AURA",
            fiscal_year=2025,
            fiscal_quarter="Q4",
            claim_text="Our gross margins remained resilient.",
            case_id="AURA_001",
        )

        assert isinstance(verdict, AuditVerdict)
        assert verdict.ticker == "AURA"
        assert verdict.is_discrepancy is True
        assert verdict.divergence_type == DivergenceType.MARGIN_DILUTION
        assert verdict.materiality == MaterialityTier.CRITICAL
        assert verdict.confidence == 0.92
        assert evaluator.last_telemetry["prompt_tokens"] == 1200
        assert evaluator.last_telemetry["completion_tokens"] == 3



def test_leakage_verifier_catches_openrouter_api_key():
    verifier = LeakageVerifier()
    leak_sample = "export OPENROUTER_API_KEY='sk-or-v1-abcdef1234567890abcdef1234567890'"
    secrets = verifier.scan_text_for_secrets(leak_sample)
    assert len(secrets) >= 1
    assert any("sk-or-v1" in s for s in secrets)


def test_normalize_decision_dict_enveloped_decision_model():
    from src.evaluators.openrouter_decider import normalize_decision_dict

    raw_router_output = {
        "decision": {
            "verdict": "CONTRADICTED",
            "divergence_category": "MARGIN CONTRACTION",
            "materiality_level": "CRITICAL",
            "confidence": "96.5%",
            "summary": "Gross margins contracted 1800 bps."
        }
    }
    norm = normalize_decision_dict(raw_router_output)
    assert norm["is_discrepancy"] is True
    assert norm["divergence_type"] == "MARGIN_DILUTION"
    assert norm["materiality"] == "CRITICAL"
    assert norm["confidence"] == 0.965


def test_normalize_decision_dict_string_booleans_and_aliases():
    from src.evaluators.openrouter_decider import normalize_decision_dict

    # False string boolean should not evaluate to True
    clean_supported = {
        "is_discrepancy": "false",
        "divergence_type": "NONE",
        "confidence": 0.12
    }
    norm1 = normalize_decision_dict(clean_supported)
    assert norm1["is_discrepancy"] is False
    assert norm1["divergence_type"] == "NONE"

    # Capex sinkhole alias
    capex_case = {
        "verdict": "DISCREPANCY",
        "divergence": "CAPEX_DRAIN",
        "severity": "HIGH",
        "confidence": 0.89
    }
    norm2 = normalize_decision_dict(capex_case)
    assert norm2["is_discrepancy"] is True
    assert norm2["divergence_type"] == "CAPITAL_SINKHOLE"
    assert norm2["materiality"] == "HIGH"


def test_extract_json_payload_trailing_comma_and_multiple_blocks():
    # Model producing thoughts in first block, final json in second block with trailing comma
    raw_response = (
        "Preliminary scratchpad:\n"
        "```json\n"
        "{\"draft_step\": 1}\n"
        "```\n\n"
        "Final verified audit result:\n"
        "```json\n"
        "{\n"
        '  "is_discrepancy": true,\n'
        '  "divergence_type": "MARGIN_DILUTION",\n'
        '  "confidence": 0.95,\n'
        "}\n"
        "```\n"
    )
    parsed = extract_json_payload(raw_response)
    assert parsed["is_discrepancy"] is True
    assert parsed["divergence_type"] == "MARGIN_DILUTION"


def test_parse_float_or_none_and_fact_check_resilience(test_db):
    from src.evaluators.openrouter_decider import _parse_float_or_none

    assert _parse_float_or_none(None) is None
    assert _parse_float_or_none("") is None
    assert _parse_float_or_none(42.5) == 42.5
    assert _parse_float_or_none("42.5") == 42.5
    assert _parse_float_or_none("$160.0M") == 160.0
    assert _parse_float_or_none("74.5%") == 74.5
    assert _parse_float_or_none("-0.228") == -0.228
    assert _parse_float_or_none("accelerated") is None
    assert _parse_float_or_none("N/A") is None

    # Test evaluating mock response containing non-numeric claimed_value
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "is_discrepancy": True,
                        "divergence_type": "MARGIN_DILUTION",
                        "materiality": "CRITICAL",
                        "confidence": 0.95,
                        "summary": "Margin diluted.",
                        "supporting_evidence": ["Evidence 1"],
                        "fact_checks": [
                            {
                                "metric": "growth_rate",
                                "claimed_value": "accelerated",  # Non-numeric string
                                "audited_value": "$160M",
                                "delta_percent": None,
                                "is_verified": False,
                                "explanation": "Qualitative claim."
                            }
                        ]
                    })
                }
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50}
    }

    evaluator = OpenRouterDecisionEvaluator(test_db, model="mock-model", api_key="sk-test-mock-key")
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        verdict = evaluator.evaluate("AURA", 2025, "Q4", "Claim", case_id="test_fc")
        assert verdict.is_discrepancy is True
        assert len(verdict.fact_checks) == 1
        assert verdict.fact_checks[0].claimed_value is None
        assert verdict.fact_checks[0].audited_value == 160.0


