class PyselyError(Exception):
    """Base error for Pysely."""


class InvalidQueryError(PyselyError):
    """Raised when a query cannot produce valid SQL."""


class UnsupportedFeatureError(PyselyError):
    """Raised when a dialect cannot support a requested operation."""


class NoResultError(PyselyError):
    """Raised when a query expected a row but returned none."""


class ClosedClientError(PyselyError):
    """Raised when execution is attempted after client shutdown."""
