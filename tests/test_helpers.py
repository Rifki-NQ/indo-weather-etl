import pytest
from pathlib import Path
from dotenv import load_dotenv
from src.main import get_env, setup_logging

ADM4_CODE = "32.16.20.2003"
ENV_DB_KEY = "DATABASE_URL"


def test_get_env_return_expected_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_DB_KEY, raising=False)
    monkeypatch.chdir(tmp_path)
    env_path = Path(tmp_path / ".env")
    env_path.touch()
    env_path.write_text(
        'DATABASE_URL="postgresql+asyncpg://user:pass@host/neondb?ssl=require"'
    )

    load_dotenv(env_path)
    value = get_env(ENV_DB_KEY)
    assert value == "postgresql+asyncpg://user:pass@host/neondb?ssl=require"


def test_get_env_file_not_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_DB_KEY, raising=False)
    monkeypatch.chdir(tmp_path)

    load_dotenv(tmp_path / ".env")
    with pytest.raises(RuntimeError):
        get_env(ENV_DB_KEY)


def test_get_env_invalid_env_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_DB_KEY, raising=False)
    monkeypatch.chdir(tmp_path)
    env_path = Path(tmp_path / ".env")
    env_path.touch()
    env_path.write_text(
        'DATABASE_URL_INVALID="postgresql+asyncpg://user:pass@host/neondb?ssl=require"'
    )

    load_dotenv(env_path)
    with pytest.raises(RuntimeError):
        get_env(ENV_DB_KEY)


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
