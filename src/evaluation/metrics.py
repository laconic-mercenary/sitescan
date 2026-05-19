from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class BinarySegmentationMetrics:
    threshold: float
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    iou: float
    precision: float
    recall: float
    f1: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_binary_metrics(
    probabilities: np.ndarray,
    mask: np.ndarray,
    threshold: float,
) -> BinarySegmentationMetrics:
    prediction = probabilities >= threshold
    target = mask > 0

    true_positive = int(np.count_nonzero(prediction & target))
    false_positive = int(np.count_nonzero(prediction & ~target))
    true_negative = int(np.count_nonzero(~prediction & ~target))
    false_negative = int(np.count_nonzero(~prediction & target))

    iou = safe_divide(true_positive, true_positive + false_positive + false_negative)
    precision = safe_divide(true_positive, true_positive + false_positive)
    recall = safe_divide(true_positive, true_positive + false_negative)
    f1 = safe_divide(2 * true_positive, 2 * true_positive + false_positive + false_negative)

    return BinarySegmentationMetrics(
        threshold=threshold,
        true_positive=true_positive,
        false_positive=false_positive,
        true_negative=true_negative,
        false_negative=false_negative,
        iou=iou,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def threshold_sweep(
    probabilities: np.ndarray,
    mask: np.ndarray,
    thresholds: list[float],
) -> list[BinarySegmentationMetrics]:
    return [compute_binary_metrics(probabilities, mask, threshold) for threshold in thresholds]
