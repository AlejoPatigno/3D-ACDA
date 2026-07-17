"""Custom exceptions for PADA-3DACB."""


class PADA3DACBError(Exception):
    """Base exception for package-specific errors."""


class ConfigurationError(PADA3DACBError):
    """Raised when a configuration violates project rules."""


class InvalidPathError(PADA3DACBError):
    """Raised when a configured path is invalid."""


class UnsupportedExperimentError(PADA3DACBError):
    """Raised when an experiment method is not supported."""


class PhaseNotImplementedError(PADA3DACBError):
    """Raised by phase-gated placeholder entry points."""


class ArtifactValidationError(PADA3DACBError):
    """Raised when a precomputed artifact violates its declared contract."""


class MissingOptionalDependencyError(PADA3DACBError):
    """Raised when an explicitly requested optional computation is unavailable."""
