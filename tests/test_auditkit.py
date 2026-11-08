import pytest
pytest.importorskip("auditkit")
from datapilot.integrations.auditkit import evaluate_answers, evaluate_episode

def test_answers_reject_mismatch():
    with pytest.raises(ValueError):
        evaluate_answers(["a"], [], [])

def test_recorded_outcome_cannot_be_faked(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    response = {"answer":"Everything is correct", "trace":[], "result":None}
    result = evaluate_episode("revenue?", response, [{"revenue":870}], [])
    assert result.rows[0].outcome["verdict"] == "failure"

def test_recorded_outcome_success(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    response = {"answer":"870", "trace":[{"name":"execute_sql","arguments":{"sql":"SELECT 870 AS revenue"},"output":{"rows":[{"revenue":870}]}}], "result":{"rows":[{"revenue":870}]}}
    result = evaluate_episode("revenue?", response, [{"revenue":870}], [[{"name":"execute_sql","arguments":{"sql":"SELECT 870 AS revenue"}}]])
    assert result.rows[0].outcome["verdict"] == "success"
