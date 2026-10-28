"""Unit tests for Brier score and Expected Calibration Error (ECE)."""

import pytest
from src.eval.calibration import brier_score, expected_calibration_error


def test_brier_score_perfect_predictions():
    y_true = [1, 0, 1, 0]
    y_prob = [1.0, 0.0, 1.0, 0.0]
    assert brier_score(y_true, y_prob) == 0.0


def test_brier_score_completely_wrong():
    y_true = [1, 0, 1, 0]
    y_prob = [0.0, 1.0, 0.0, 1.0]
    assert brier_score(y_true, y_prob) == 1.0


def test_brier_score_uniform_probabilities():
    y_true = [1, 0, 1, 0]
    y_prob = [0.5, 0.5, 0.5, 0.5]
    assert brier_score(y_true, y_prob) == 0.25


def test_ece_perfect_calibration():
    # 10 samples predicted with 0.8 probability, exactly 8 positive (80% accuracy)
    y_true = [1] * 8 + [0] * 2
    y_prob = [0.8] * 10
    ece = expected_calibration_error(y_true, y_prob, n_bins=10)
    assert abs(ece - 0.0) < 1e-6


def test_ece_miscalibrated():
    # Model is 100% confident (1.0), but accuracy is only 50%
    y_true = [1, 0, 1, 0]
    y_prob = [1.0, 1.0, 1.0, 1.0]
    ece = expected_calibration_error(y_true, y_prob, n_bins=10)
    assert abs(ece - 0.5) < 1e-6


def test_calibration_validation_errors():
    with pytest.raises(ValueError, match="Length mismatch"):
        brier_score([1, 0], [0.5])

    with pytest.raises(ValueError, match="empty sequence"):
        brier_score([], [])

    with pytest.raises(ValueError, match="0 or 1"):
        brier_score([2], [0.5])

    with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
        brier_score([1], [1.5])

    with pytest.raises(ValueError, match="n_bins must be at least 1"):
        expected_calibration_error([1], [0.5], n_bins=0)
