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
