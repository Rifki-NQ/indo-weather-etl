from pathlib import Path

TEST_DIR = Path(__file__).parent


def test_dir() -> Path:
    return TEST_DIR


def mock_data_dir() -> Path:
    return TEST_DIR / "mock_data"
