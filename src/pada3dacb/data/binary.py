"""Compatibility import surface for Phase 18B binary records and splits."""

from pada3dacb.binary import (
    BINARY_CLASS_ORDER,
    BINARY_CLASS_TO_INDEX,
    BINARY_MAPPING_CONTRACT,
    SPLIT_DISPOSITION,
    BinaryLabelError,
    BinarySubjectRecord,
    OasisEvidence,
    build_binary_target_partition,
    generate_binary_source_folds,
    load_verified_oasis_metadata,
    map_adni_label,
    select_best_checkpoint_by_source_validation_macro_f1,
)

__all__ = [
    "BINARY_CLASS_ORDER", "BINARY_CLASS_TO_INDEX", "BINARY_MAPPING_CONTRACT",
    "SPLIT_DISPOSITION", "BinaryLabelError", "BinarySubjectRecord", "OasisEvidence",
    "build_binary_target_partition", "generate_binary_source_folds",
    "select_best_checkpoint_by_source_validation_macro_f1",
    "load_verified_oasis_metadata", "map_adni_label",
]
