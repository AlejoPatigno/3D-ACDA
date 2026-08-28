"""Custom exceptions for 3D-ACDA."""


class ACDA3DError(Exception):
    """Base exception for package-specific errors."""


class ConfigurationError(ACDA3DError):
    """Raised when a configuration violates project rules."""


class InvalidPathError(ACDA3DError):
    """Raised when a configured path is invalid."""


class UnsupportedExperimentError(ACDA3DError):
    """Raised when an experiment method is not supported."""


class PhaseNotImplementedError(ACDA3DError):
    """Raised by phase-gated placeholder entry points."""


class ArtifactValidationError(ACDA3DError):
    """Raised when a precomputed artifact violates its declared contract."""


class MissingOptionalDependencyError(ACDA3DError):
    """Raised when an explicitly requested optional computation is unavailable."""


class DatasetContractError(ACDA3DError):
    """Raised when a subject record or dataset role violates its contract."""


class SplitValidationError(ACDA3DError):
    """Raised when deterministic split manifests are invalid or incompatible."""


class ModelContractError(ACDA3DError, ValueError):
    """Raised when model inputs or architecture settings violate their contract."""


class CheckpointMigrationError(ACDA3DError, RuntimeError):
    """Raised when a legacy checkpoint cannot be migrated without ambiguity."""


class LossContractError(ACDA3DError, ValueError):
    """Raised when scientific-loss tensors violate their declared contract."""


class TrainingRuntimeError(ACDA3DError, RuntimeError):
    """Raised when fixed-epoch training cannot proceed safely."""


class ExperimentValidationError(ACDA3DError, RuntimeError):
    """Raised when a source-only experiment input or reusable run is incompatible."""
