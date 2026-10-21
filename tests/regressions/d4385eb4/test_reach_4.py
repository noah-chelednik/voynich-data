# tests/regressions/d4385eb4/test_reach_4.py
import datasets
import huggingface_hub.constants as hub_constants

from tests import test_staging as gate


def test_staging_loader_enforces_offline_after_dependency_import(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HF_DATASETS_OFFLINE", "0")
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setattr(datasets.config, "HF_HUB_OFFLINE", False)
    monkeypatch.setattr(datasets.config, "HF_DATASETS_OFFLINE", False)
    monkeypatch.setattr(hub_constants, "HF_HUB_OFFLINE", False)

    def observe_load(*args, **kwargs):
        assert datasets.config.HF_HUB_OFFLINE, "datasets remains online"
        assert hub_constants.HF_HUB_OFFLINE, "huggingface_hub remains online"
        return object()

    monkeypatch.setattr(datasets, "load_dataset", observe_load)

    gate.load(tmp_path / "repository", "default", tmp_path / "cache")
