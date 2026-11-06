from app.storage import list_results, save_result


def test_save_and_list_results_with_sqlite(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'history.db'}")
    record = {
        "run_id": "run-123",
        "task_id": "task-123",
        "success": True,
        "score": 1.0,
        "cost_usd": None,
    }
    assert save_result(record, "test")
    rows = list_results(limit=10, offset=0)
    assert rows == [record]


def test_storage_is_disabled_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert save_result({"run_id": "r", "task_id": "t"}) is False
