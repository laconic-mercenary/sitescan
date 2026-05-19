import numpy as np

from src.evaluation.metrics import compute_binary_metrics


def test_compute_binary_metrics() -> None:
    probabilities = np.array([[0.9, 0.8], [0.2, 0.1]], dtype="float32")
    mask = np.array([[1, 0], [1, 0]], dtype="uint8")

    metrics = compute_binary_metrics(probabilities, mask, threshold=0.5)

    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.true_negative == 1
    assert metrics.false_negative == 1
    assert metrics.iou == 1 / 3
