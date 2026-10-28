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


def test_maximum_calibration_error():
    from src.eval.calibration import maximum_calibration_error

    # Model is 100% confident (1.0), but accuracy is only 50%
    y_true = [1, 0, 1, 0]
    y_prob = [1.0, 1.0, 1.0, 1.0]
    mce = maximum_calibration_error(y_true, y_prob, n_bins=10)
    assert abs(mce - 0.5) < 1e-6

    # Perfectly calibrated bin
    y_true_perf = [1] * 8 + [0] * 2
    y_prob_perf = [0.8] * 10
    assert abs(maximum_calibration_error(y_true_perf, y_prob_perf, n_bins=10) - 0.0) < 1e-6


def test_binary_log_loss():
    from src.eval.calibration import binary_log_loss
    import math

    # Perfect prediction should have very small loss
    y_true = [1, 0]
    y_prob = [1.0, 0.0]
    loss = binary_log_loss(y_true, y_prob)
    assert loss < 1e-6

    # 50/50 prediction should be -ln(0.5) ≈ 0.6931
    y_prob_half = [0.5, 0.5]
    loss_half = binary_log_loss(y_true, y_prob_half)
    assert abs(loss_half - math.log(2)) < 1e-4


def test_materiality_weighted_loss():
    from src.eval.calibration import materiality_weighted_loss

    # Perfect match -> 0.0
    y_true = [1, 0, 1]
    y_pred = [1, 0, 1]
    materialities = ["CRITICAL", "HIGH", "LOW"]
    assert materiality_weighted_loss(y_true, y_pred, materialities) == 0.0

    # Miss only the CRITICAL one (weight 5.0 out of 5+3+1 = 9.0)
    y_pred_miss_crit = [0, 0, 1]
    loss = materiality_weighted_loss(y_true, y_pred_miss_crit, materialities)
    assert abs(loss - (5.0 / 9.0)) < 1e-6

    # Miss only the LOW one (weight 1.0 out of 9.0)
    y_pred_miss_low = [1, 0, 0]
    loss_low = materiality_weighted_loss(y_true, y_pred_miss_low, materialities)
    assert abs(loss_low - (1.0 / 9.0)) < 1e-6
