import uuid

from app.services.run_engine import RunLabelSpec, decide


def spec(name: str, threshold: float) -> RunLabelSpec:
    return RunLabelSpec(
        position=0,
        label_id=uuid.uuid4(),
        name=name,
        filter_condition="c",
        threshold=threshold,
        condition_hash="h",
    )


def test_label_matches_when_probability_reaches_its_own_threshold():
    labels = [spec("a", 0.5), spec("b", 0.9), spec("c", 0.3)]
    decisions = decide({"a": 0.5, "b": 0.89, "c": 0.31}, labels)
    assert [(d.spec.name, d.matched) for d in decisions] == [("a", True), ("b", False), ("c", True)]
    assert decisions[1].probability == 0.89


def test_auth_errors_are_fatal():
    from app.services.jev import FATAL_STATUSES, JevError

    assert {401, 402, 403} <= set(FATAL_STATUSES)
    assert JevError("x", fatal=True).fatal and not JevError("x").fatal
