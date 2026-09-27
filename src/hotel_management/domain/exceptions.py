class DomainError(Exception):
    """Base exception for business-rule violations."""


class ValidationError(DomainError):
    """Raised when a value cannot exist in the domain."""


class NotFoundError(DomainError):
    """Raised when a requested aggregate does not exist."""


class RoomUnavailableError(DomainError):
    """Raised when a room cannot be reserved for a date range."""


class InvalidBookingStateError(DomainError):
    """Raised when a booking command is invalid for its current state."""
