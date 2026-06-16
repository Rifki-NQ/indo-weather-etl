class DomainError(Exception):
    """Base exception for all business / logic errors"""

    pass


class ExtractorError(DomainError):
    """Base exception for extractor error"""

    pass


class LoaderError(DomainError):
    """Base exception for loader error"""

    pass


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


class DBNotInitializedError(LoaderError):
    """Raised when the setup_db() has not called"""

    def __init__(self, message: str) -> None:
        super().__init__(f"Error: {message}")

    pass
