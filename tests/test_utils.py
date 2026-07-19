import pytest
from collections.abc import Iterable
from pathlib import Path
from dotenv import load_dotenv
from tests.paths import mock_data_dir
from src.main import get_env, setup_logging
from src.core.utils import yield_csv_value
from src.core.exceptions import (
    NotFileError,
    EmptyFileError,
    NotCSVFileError,
    InvalidColumnName,
)

ENV_DB_KEY = "DATABASE_URL"
ENV_ADM4_CODES_KEY = "ADM4_CODES_PATH"
DB_VALID_URL = "postgresql+asyncpg://user:pass@host/neondb?ssl=require"
ADM4_CODES_VALID_PATH = mock_data_dir() / "mock_adm4_codes.csv"
FILE_NOT_EXISTS_PATH = mock_data_dir() / "non_exist_file.csv"
NOT_A_FILE_PATH = mock_data_dir() / "mock_not_a_file"  # a folder, not a file
EMPTY_FILE_PATH = mock_data_dir() / "mock_empty_file.csv"
NOT_A_CSV_PATH = (
    mock_data_dir() / "mock_not_a_csv.txt"
)  # valid CSV-shaped content with wrong extension


def create_and_load_temporary_env(
    temp_path: Path, monkeypatch: pytest.MonkeyPatch, db_url: str, adm4_code_path: str
) -> None:
    """
    Delete previous envs then change cwd to tmp_path,
    create and write new .env file to the tmp_path,
    lastly, load the env with load_dotenv().
    """
    monkeypatch.delenv(ENV_DB_KEY, raising=False)
    monkeypatch.delenv(ENV_ADM4_CODES_KEY, raising=False)
    monkeypatch.chdir(temp_path)
    env_path = Path(temp_path / ".env")
    env_path.touch()
    env_path.write_text(f"{ENV_DB_KEY}={db_url}\n{ENV_ADM4_CODES_KEY}={adm4_code_path}")
    load_dotenv(env_path)


def test_get_env_return_expected_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test if get_env() return expected value."""
    create_and_load_temporary_env(
        tmp_path, monkeypatch, DB_VALID_URL, str(ADM4_CODES_VALID_PATH)
    )
    db_url = get_env(ENV_DB_KEY)
    adm4_codes_path = get_env(ENV_ADM4_CODES_KEY)
    assert db_url == DB_VALID_URL
    assert adm4_codes_path == str(ADM4_CODES_VALID_PATH)


def test_get_env_file_not_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test when .env is missing from cwd."""
    monkeypatch.delenv(ENV_DB_KEY, raising=False)
    monkeypatch.chdir(tmp_path)

    load_dotenv(tmp_path / ".env")
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
    """Test if setup_logging() creates '.log' file inside 'logs/' folder"""
    monkeypatch.chdir(tmp_path)
    setup_logging()
    log_files = list((tmp_path / "logs").glob("*.log"))
    assert len(log_files) == 1


def test_yield_csv_value_return_iterable() -> None:
    excepted_iterable = yield_csv_value(ADM4_CODES_VALID_PATH, "")
    assert isinstance(excepted_iterable, Iterable)


def test_yield_csv_value_yield_expected_data() -> None:
    """Test if the first 5 yielded rows is as expected."""
    values = yield_csv_value(ADM4_CODES_VALID_PATH, "Kode")
    expected = [
        "32.01.01.1001",
        "32.01.01.1002",
        "32.01.01.1003",
        "32.01.01.1004",
        "32.01.01.1005",
    ]
    for i, value in enumerate(values):
        if i >= len(expected):
            break
        assert value == expected[i]


def test_yield_csv_value_file_not_exists() -> None:
    with pytest.raises(FileNotFoundError):
        yield_csv_value(FILE_NOT_EXISTS_PATH, "")


def test_yield_csv_value_path_not_a_file() -> None:
    with pytest.raises(NotFileError) as exc_info:
        yield_csv_value(NOT_A_FILE_PATH, "")
    assert exc_info.value.filepath == NOT_A_FILE_PATH


def test_yield_csv_value_file_is_empty() -> None:
    with pytest.raises(EmptyFileError) as exc_info:
        yield_csv_value(EMPTY_FILE_PATH, "")
    assert exc_info.value.filepath == EMPTY_FILE_PATH


def test_yield_csv_value_file_not_a_csv() -> None:
    with pytest.raises(NotCSVFileError) as exc_info:
        yield_csv_value(NOT_A_CSV_PATH, "")
    assert exc_info.value.filepath == NOT_A_CSV_PATH.name


def test_yield_csv_value_invalid_column_name() -> None:
    """
    Test that an InvalidColumnName is raised when the given 'column_name'
    argument does not exist in the CSV file.

    Note: since the function under test returns an Iterable, the
    exception isn't raised until the Iterable is actually iterated over.
    """
    column_name = "non_existent_column"
    values = yield_csv_value(ADM4_CODES_VALID_PATH, column_name)
    with pytest.raises(InvalidColumnName) as exc_info:
        for _ in values:
            break
    assert exc_info.value.column_name == column_name
