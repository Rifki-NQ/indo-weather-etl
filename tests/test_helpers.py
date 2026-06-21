import pytest
from pathlib import Path
from src.main import setup_db_url_and_path, setup_logging

ADM4_CODE = "32.16.20.2003"


def test_setup_db_url_and_path_creates_database_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    setup_db_url_and_path(ADM4_CODE)
    assert (tmp_path / "database").is_dir()


def test_setup_db_url_and_path_returns_correct_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    db_url = setup_db_url_and_path(ADM4_CODE)
    assert db_url == f"sqlite:///database/{ADM4_CODE}_weather_forecast.db"


def test_setup_logging_creates_logs_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    setup_logging()
    assert (tmp_path / "logs").is_dir()


def test_setup_logging_creates_log_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    setup_logging()
    log_files = list((tmp_path / "logs").glob("*.log"))
    assert len(log_files) == 1
