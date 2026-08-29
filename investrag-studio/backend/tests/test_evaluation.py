from investrag.evaluation import ndcg_at_k, recall_at_k, reciprocal_rank, success_at_k


def test_ir_metrics_keep_success_and_recall_distinct() -> None:
    relevant = {"a", "b"}
    retrieved = ["x", "a", "y"]
    assert success_at_k(relevant, retrieved, 3) == 1.0
    assert recall_at_k(relevant, retrieved, 3) == 0.5
    assert reciprocal_rank(relevant, retrieved, 3) == 0.5
    assert ndcg_at_k({"a": 2, "b": 1}, retrieved, 3) > 0
