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


class DatasetContractError(PADA3DACBError):
    """Raised when a subject record or dataset role violates its contract."""


class SplitValidationError(PADA3DACBError):
    """Raised when deterministic split manifests are invalid or incompatible."""


class ModelContractError(PADA3DACBError, ValueError):
    """Raised when model inputs or architecture settings violate their contract."""


class CheckpointMigrationError(PADA3DACBError, RuntimeError):
    """Raised when a legacy checkpoint cannot be migrated without ambiguity."""


class LossContractError(PADA3DACBError, ValueError):
    """Raised when scientific-loss tensors violate their declared contract."""


class TrainingRuntimeError(PADA3DACBError, RuntimeError):
    """Raised when fixed-epoch training cannot proceed safely."""


class ExperimentValidationError(PADA3DACBError, RuntimeError):
    """Raised when a source-only experiment input or reusable run is incompatible."""
