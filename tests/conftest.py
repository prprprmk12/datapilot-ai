import pytest

@pytest.fixture(autouse=True)
def temporary_run_store(tmp_path,monkeypatch):
    from datapilot import api
    from datapilot.runs import RunStore
    from datapilot.config import Settings
    monkeypatch.setattr(api,'settings',Settings(_env_file=None,model_provider='demo'))
    monkeypatch.setattr(api,'run_store',RunStore(tmp_path/'runs.sqlite3'))
