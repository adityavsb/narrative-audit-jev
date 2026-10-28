"""Probability calibration metrics: Brier Score (1950) and Expected Calibration Error (Guo et al. 2017)."""

from __future__ import annotations

from typing import Sequence


def brier_score(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    """Compute the Brier Score for binary probabilistic predictions.

    Args:
        y_true: Sequence of binary ground truth indicators in {0, 1}.
        y_prob: Sequence of predicted probabilities in [0.0, 1.0].

    Returns:
        Mean squared error between predicted probabilities and binary outcomes.
        Lower values indicate better calibrated and sharper probabilistic predictions.
    """
    if len(y_true) != len(y_prob):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true)} elements, y_prob has {len(y_prob)} elements."
        )
    if not y_true:
        raise ValueError("Cannot calculate Brier score on an empty sequence.")

    total_sq_err = 0.0
    for yt, yp in zip(y_true, y_prob):
        if yt not in (0, 1):
            raise ValueError(f"y_true values must be 0 or 1, got {yt}")
        if not (0.0 <= yp <= 1.0):
            raise ValueError(f"y_prob values must be in [0.0, 1.0], got {yp}")
        total_sq_err += (yp - float(yt)) ** 2

    return total_sq_err / len(y_true)


def expected_calibration_error(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> float:
    """Compute the Expected Calibration Error (ECE) with equal-width probability bins.

    Partitions [0.0, 1.0] into M equal-width bins, computing the weighted absolute
    difference between empirical accuracy and average confidence across bins:
        ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|

    Args:
        y_true: Sequence of binary ground truth indicators in {0, 1}.
        y_prob: Sequence of predicted probabilities in [0.0, 1.0].
        n_bins: Number of equal-width bins (default: 10).

    Returns:
        Expected Calibration Error in [0.0, 1.0]. Lower values indicate better calibration.
    """
    if len(y_true) != len(y_prob):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true)} elements, y_prob has {len(y_prob)} elements."
        )
    if not y_true:
        raise ValueError("Cannot calculate ECE on an empty sequence.")
    if n_bins < 1:
        raise ValueError(f"n_bins must be at least 1, got {n_bins}")

    n_samples = len(y_true)
    bins = [[] for _ in range(n_bins)]

    for yt, yp in zip(y_true, y_prob):
        if yt not in (0, 1):
            raise ValueError(f"y_true values must be 0 or 1, got {yt}")
        if not (0.0 <= yp <= 1.0):
            raise ValueError(f"y_prob values must be in [0.0, 1.0], got {yp}")

        # Bin index: [0, 1/M), [1/M, 2/M), ..., [(M-1)/M, 1.0]
        bin_idx = int(yp * n_bins)
        if bin_idx >= n_bins:
            bin_idx = n_bins - 1
        bins[bin_idx].append((float(yt), float(yp)))

    ece = 0.0
    for bin_items in bins:
        if not bin_items:
            continue
        bin_size = len(bin_items)
        avg_acc = sum(item[0] for item in bin_items) / bin_size
        avg_conf = sum(item[1] for item in bin_items) / bin_size
        ece += (bin_size / n_samples) * abs(avg_acc - avg_conf)

    return ece


def maximum_calibration_error(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> float:
    """Compute the Maximum Calibration Error (MCE) across equal-width probability bins.

    Computes the maximum deviation between empirical accuracy and average confidence:
        MCE = max_{m=1}^M |acc(B_m) - conf(B_m)|

    Args:
        y_true: Sequence of binary ground truth indicators in {0, 1}.
        y_prob: Sequence of predicted probabilities in [0.0, 1.0].
        n_bins: Number of equal-width bins (default: 10).

    Returns:
        Maximum Calibration Error in [0.0, 1.0]. Lower values indicate better calibration.
    """
    if len(y_true) != len(y_prob):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true)} elements, y_prob has {len(y_prob)} elements."
        )
    if not y_true:
        raise ValueError("Cannot calculate MCE on an empty sequence.")
    if n_bins < 1:
        raise ValueError(f"n_bins must be at least 1, got {n_bins}")

    bins = [[] for _ in range(n_bins)]
    for yt, yp in zip(y_true, y_prob):
        if yt not in (0, 1):
            raise ValueError(f"y_true values must be 0 or 1, got {yt}")
        if not (0.0 <= yp <= 1.0):
            raise ValueError(f"y_prob values must be in [0.0, 1.0], got {yp}")

        bin_idx = int(yp * n_bins)
        if bin_idx >= n_bins:
            bin_idx = n_bins - 1
        bins[bin_idx].append((float(yt), float(yp)))

    max_err = 0.0
    for bin_items in bins:
        if not bin_items:
            continue
        bin_size = len(bin_items)
        avg_acc = sum(item[0] for item in bin_items) / bin_size
        avg_conf = sum(item[1] for item in bin_items) / bin_size
        gap = abs(avg_acc - avg_conf)
        if gap > max_err:
            max_err = gap

    return max_err


def binary_log_loss(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    eps: float = 1e-15,
) -> float:
    """Compute the Negative Log-Likelihood (Binary Cross-Entropy Loss).

    Args:
        y_true: Sequence of binary ground truth indicators in {0, 1}.
        y_prob: Sequence of predicted probabilities in [0.0, 1.0].
        eps: Small epsilon for clipping probabilities to avoid log(0).

    Returns:
        Mean negative log-likelihood across all predictions. Lower is better.
    """
    import math

    if len(y_true) != len(y_prob):
        raise ValueError(
            f"Length mismatch: y_true has {len(y_true)} elements, y_prob has {len(y_prob)} elements."
        )
    if not y_true:
        raise ValueError("Cannot calculate log loss on an empty sequence.")

    total_loss = 0.0
    for yt, yp in zip(y_true, y_prob):
        if yt not in (0, 1):
            raise ValueError(f"y_true values must be 0 or 1, got {yt}")
        if not (0.0 <= yp <= 1.0):
            raise ValueError(f"y_prob values must be in [0.0, 1.0], got {yp}")

        p = max(min(yp, 1.0 - eps), eps)
        total_loss += -(yt * math.log(p) + (1 - yt) * math.log(1.0 - p))

    return total_loss / len(y_true)


def materiality_weighted_loss(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    materialities: Sequence[str],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Compute SEC SAB 99 Materiality-Weighted Penalty.

    Weights misclassifications according to their accounting significance:
    missing a CRITICAL scheme is penalized more heavily than a minor LOW timing mismatch.

    Args:
        y_true: Ground truth binary labels in {0, 1}.
        y_pred: Predicted binary labels in {0, 1}.
        materialities: Sequence of materiality strings (CRITICAL, HIGH, MODERATE, LOW, NONE).
        weights: Optional dictionary mapping materiality tiers to penalty weights.

    Returns:
        Normalized materiality penalty in [0.0, 1.0]. Lower is better.
    """
    if not (len(y_true) == len(y_pred) == len(materialities)):
        raise ValueError("y_true, y_pred, and materialities must have identical lengths.")
    if not y_true:
        raise ValueError("Cannot calculate materiality loss on an empty sequence.")

    default_weights = {
        "CRITICAL": 5.0,
        "HIGH": 3.0,
        "MODERATE": 2.0,
        "LOW": 1.0,
        "NONE": 1.0,
    }
    tier_weights = weights or default_weights

    penalty_sum = 0.0
    total_possible_weight = 0.0

    for yt, yp, mat in zip(y_true, y_pred, materialities):
        w = tier_weights.get(mat.upper(), 1.0)
        total_possible_weight += w
        if yt != yp:
            penalty_sum += w

    return penalty_sum / total_possible_weight if total_possible_weight > 0 else 0.0
