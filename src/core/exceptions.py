from pathlib import Path


class DomainError(Exception):
    """Base exception for all business / logic errors"""


class ExtractorError(DomainError):
    """Base exception for extractor error"""


class LoaderError(DomainError):
    """Base exception for loader error"""


class FileHandlingError(DomainError):
    """Base exception for all file handling error"""


class MaxRetryAttemptError(ExtractorError):
    """Raised when the maximum retry attempt has reached"""

    def __init__(self, max_attempt: int) -> None:
        self.max_attempt = max_attempt
        super().__init__(f"Error: max retry attempt reached: {max_attempt}")


class InvalidAdm4CodeError(ExtractorError):
    """Raised when adm4_code is invalid and the API return status code 404"""

    def __init__(self, adm4_code: str) -> None:
        self.adm4_code = adm4_code
        super().__init__(f"Error: invalid adm4_code ({adm4_code}), API returns 404")


class EmptyForecastDataError(ExtractorError):
    """Raised when the API return empty weather forecast data"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Error: {message}")


class AllForecastDataMalformedError(ExtractorError):
    """Raised when all forecast data from the API is malformed"""

    def __init__(self, total_malformed: int) -> None:
        self.total_malformed = total_malformed
        super().__init__(
            f"Error: all forecast data from the API ({total_malformed} items) malformed"
        )


class DBNotInitializedError(LoaderError):
    """Raised when the setup_db() has not called"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Error: {message}")


class DBAlreadyInitializedError(LoaderError):
    """Raised when the setup_db() is called more than once"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Error: {message}")


class DBEngineCreationFailedError(LoaderError):
    """Raised when create_async_engine() is failed"""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        super().__init__(f"Error: engine creation failed, caused by: {exc!r}")


class DBSetupFailedError(LoaderError):
    """Raised when the setup_db() is failed or there is an error raised inside it"""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        super().__init__(f"Error: setup_db() failed, caused by: {exc!r}")


class NotFileError(FileHandlingError):
    """Raised when the given filepath is not a file"""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        super().__init__(f"Error: {filepath} is not a file")


class EmptyFileError(FileHandlingError):
    """Raised when the file is empty"""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        super().__init__(f"Error: {filepath} is empty")


class NotCSVFileError(FileHandlingError):
    """Raised when the given filepath is not a csv file"""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        super().__init__(f"Error: {filepath} is not a csv file")


class InvalidColumnName(FileHandlingError):
    """Raised when given column_name does not exist in the csv file"""

    def __init__(self, column_name: str) -> None:
        self.column_name = column_name
        super().__init__(f"Error: column {column_name} does not exist")
