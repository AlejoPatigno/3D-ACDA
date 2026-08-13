# Concept-Evaluation Specification

## Purpose

Remediate the remaining Phase 16 review blockers by establishing strict candidate provenance and configuration eligibility, enforcing safe checkpoint loading with explicit real-run authorization, and ensuring deterministic output versioning with truthful evidence reporting, without expanding the scientific feature set or altering the review lifecycle.

## Requirements

### Requirement A-1: Candidate Provenance Validation
The system MUST validate that all required candidate provenance fields are present, correctly formatted, and verifiable before permitting eligibility for real evaluation.

#### Scenario: Valid candidate provenance
- GIVEN a candidate with all required provenance fields (atlas hash, normalizer hash, ROI order hash, manifest references) present and correctly formatted
- AND the asserted atlas file exists with a verifiable hash matching the candidate's claim
- AND the asserted normalizer file exists with a verifiable hash matching the candidate's claim
- WHEN the eligibility check is performed
- THEN the candidate is considered eligible for further evaluation steps

#### Scenario: Missing provenance field
- GIVEN a candidate missing a required provenance field (e.g., atlas hash)
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

#### Scenario: Malformed provenance field
- GIVEN a candidate with a malformed hash (e.g., incorrect length, non-hex characters)
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

#### Scenario: Unverifiable atlas hash
- GIVEN a candidate claiming an atlas hash that does not match the actual file
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

### Requirement A-2: Artifact Binding and Hash Verification
The system MUST bind candidate artifact claims to actual canonical files and verify their hashes to prevent spoofed or mismatched provenance.

#### Scenario: Atlas file binding
- GIVEN a candidate claiming a specific atlas file path and hash
- WHEN the eligibility check resolves the atlas file path and computes its hash
- THEN the computed hash MUST exactly match the claimed hash for eligibility to proceed

#### Scenario: Normalizer file binding
- GIVEN a candidate claiming a specific normalizer file path and hash
- WHEN the eligibility check resolves the normalizer file path and computes its hash
- THEN the computed hash MUST exactly match the claimed hash for eligibility to proceed

#### Scenario: Artifact file missing
- GIVEN a candidate claiming an atlas or normalizer file that does not exist on disk
- WHEN the eligibility check attempts to resolve the file path
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

### Requirement A-3: ROI Order Consistency
The system MUST enforce a single, consistent ROI label/order hash across checkpoint metadata, normalizer, atlas, candidate metadata, and runtime manager inputs for real evaluation eligibility.

#### Scenario: Consistent ROI order
- GIVEN a candidate where the checkpoint metadata, normalizer, atlas, candidate metadata, and runtime manager all report the same ROI order hash
- WHEN the eligibility check is performed
- THEN the candidate is considered eligible for further evaluation steps

#### Scenario: Inconsistent ROI order
- GIVEN a candidate where any of the following differ: checkpoint metadata ROI hash, normalizer ROI hash, atlas ROI hash, candidate metadata ROI hash, or runtime manager ROI hash
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

#### Scenario: Missing ROI order in any component
- GIVEN a candidate where any required component (checkpoint, normalizer, atlas, candidate metadata, runtime manager) lacks an ROI order hash
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

### Requirement A-4: Configuration Validation
The system MUST validate the minimum configuration required for safe discovery and real-run authorization, including type, range, assignment, and cross-field invariants.

#### Scenario: Valid configuration
- GIVEN a configuration with all required fields present, correctly typed, within valid ranges, and satisfying cross-field constraints (e.g., manifest paths exist, assigned artifacts match claims)
- WHEN the eligibility check is performed
- THEN the configuration is considered valid and does not block eligibility

#### Scenario: Missing required configuration field
- GIVEN a configuration missing a required field (e.g., atlas path)
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

#### Scenario: Invalid configuration type
- GIVEN a configuration where a field has an incorrect type (e.g., a string where an integer is expected)
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

#### Scenario: Configuration value out of range
- GIVEN a configuration where a numeric field is outside its allowed range (e.g., negative batch size)
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

#### Scenario: Failed cross-field constraint
- GIVEN a configuration where two fields have an invalid relationship (e.g., manifest path does not reference the assigned atlas file)
- WHEN the eligibility check is performed
- THEN the candidate is deemed ineligible and the evaluation halts before model loading

### Requirement A-5: Fail-Closed Eligibility Boundary
The system MUST fail closed for any candidate eligibility check, ensuring that missing, malformed, conflicting, or unverifiable provenance or configuration prevents progression to model loading, inference, statistics, or output publication.

#### Scenario: Fail closed on provenance failure
- GIVEN a candidate that fails any provenance validation (missing, malformed, or unverifiable artifact)
- WHEN the eligibility check is performed
- THEN the system halts execution before any model loading, inference, statistics computation, or output publication occurs

#### Scenario: Fail closed on configuration failure
- GIVEN a candidate that fails any configuration validation (missing, mistyped, out-of-range, or constraint-violating field)
- WHEN the eligibility check is performed
- THEN the system halts execution before any model loading, inference, statistics computation, or output publication occurs

#### Scenario: Fail closed on ROI inconsistency
- GIVEN a candidate with inconsistent ROI order hashes across required components
- WHEN the eligibility check is performed
- THEN the system halts execution before any model loading, inference, statistics computation, or output publication occurs

### Requirement B-1: Explicit Real-Run Authorization Contract
The system MUST require an explicit authorization capability before permitting any real evaluation entry point to proceed with checkpoint loading, model construction, forward pass, inference, statistics, or output publication.

#### Scenario: Authorized CLI real-mode invocation
- GIVEN a trusted caller supplying an explicit authorization capability (e.g., a validated token or flag) via the CLI real-mode entry point
- AND all eligibility checks (A-1 through A-5) have passed
- WHEN the CLI real-mode entry point is invoked
- THEN the system proceeds to checkpoint loading and subsequent evaluation steps

#### Scenario: Unauthorized CLI real-mode invocation
- GIVEN a CLI real-mode entry point invocation lacking the explicit authorization capability
- WHEN the entry point is invoked
- THEN the system halts execution before checkpoint loading, returning an unauthorized error

#### Scenario: Unauthorized direct programmatic call
- GIVEN a direct call to a real-mode function (e.g., `run_evaluation`) lacking the explicit authorization capability
- WHEN the function is invoked
- THEN the function returns an unauthorized error before any checkpoint loading, model construction, or inference occurs

#### Scenario: Authorized programmatic call with capability
- GIVEN a direct call to a real-mode function accompanied by a valid explicit authorization capability
- AND all eligibility checks (A-1 through A-5) have passed
- WHEN the function is invoked
- THEN the function proceeds to checkpoint loading and subsequent evaluation steps

### Requirement B-2: Provenance-First Safe Checkpoint Loading
The system MUST establish checkpoint file identity and verify its safety before parsing its contents, prohibiting arbitrary-object reconstruction for untrusted checkpoint content.

#### Scenario: Checkpoint file identity established first
- GIVEN a checkpoint file path provided for loading
- WHEN the system prepares to load the checkpoint
- THEN the system first verifies the file's existence and computes its hash to establish identity
- AND only after identity verification does it proceed to safe tensor-only parsing

#### Scenario: Safe tensor-only loading path used
- GIVEN a checkpoint file whose identity has been established
- WHEN the system loads the checkpoint
- THEN it uses a tensor-only loading mechanism (e.g., `torch.load(weights_only=True)`) and rejects any attempt to load arbitrary objects

#### Scenario: Rejection of unsupported checkpoint format
- GIVEN a checkpoint file that requires arbitrary-object reconstruction to load (e.g., contains custom Python objects)
- WHEN the system attempts to load the checkpoint via the tensor-only path
- THEN the load fails and the system raises an error indicating unsupported format, without falling back to unsafe loading

#### Scenario: No `weights_only=False` before provenance
- GIVEN an untrusted checkpoint file
- WHEN the system processes a real evaluation request
- THEN at no point is `torch.load(weights_only=False)` or equivalent called before the file's identity and safety are verified

### Requirement B-3: Authorization-Provenance Checkpoint Ordering
The system MUST enforce that explicit authorization and complete provenance validation occur before any checkpoint loading, model construction, forward pass, inference, statistics computation, or output publication in real evaluation mode.

#### Scenario: Authorization before checkpoint load
- GIVEN a real evaluation request with valid authorization
- AND all eligibility checks (A-1 through A-5) have passed
- WHEN the evaluation proceeds
- THEN the authorization check is completed before any checkpoint file is opened for reading

#### Scenario: Provenance before checkpoint load
- GIVEN a real evaluation request that has passed authorization
- AND all eligibility checks (A-1 through A-5) have passed
- WHEN the evaluation proceeds
- THEN the provenance and artifact binding checks (A-1 and A-2) are completed before any checkpoint file is opened for reading

#### Scenario: No model construction before authorization
- GIVEN a real evaluation request lacking authorization
- WHEN the evaluation process begins
- THEN no model architecture is instantiated, no weights are allocated, and no forward pass is attempted before the authorization failure is raised

### Requirement B-4: Synthetic and Validate-Only Mode Determinism
The system MUST preserve deterministic behavior in synthetic and validate-only modes, restricting them to explicitly designated synthetic fixtures and prohibiting real checkpoint usage. Every synthetic or validate-only execution MUST receive a verified fixture manifest with an explicit synthetic/fixture marker, the expected manifest SHA-256, safe paths contained within an allowed root, and per-file hashes; a boolean flag alone is invalid.

#### Scenario: Synthetic mode uses designated fixtures
- GIVEN a request to run in synthetic mode
- WHEN the system loads data and checkpoints
- THEN it uses only explicitly designated synthetic fixtures (e.g., fixed synthetic data and checkpoint files) and rejects any attempt to use real ADNI/OASIS data or checkpoints

#### Scenario: Validate-only mode uses designated fixtures
- GIVEN a request to run in validate-only mode
- WHEN the system loads data and checkpoints
- THEN it uses only explicitly designated synthetic fixtures and rejects any attempt to use real ADNI/OASIS data or checkpoints

#### Scenario: Synthetic mode determinism
- GIVEN two identical synthetic mode runs with the same inputs and fixtures
- WHEN each run completes
- THEN they produce identical outputs (within floating-point tolerance) and side effects

### Requirement B-5: Unauthorized Direct Call Prevention
The system MUST ensure that no direct programmatic entry point to real evaluation logic can bypass the explicit authorization requirement.

#### Scenario: Direct call to inference function blocked
- GIVEN a direct call to the core inference function (e.g., `run_inference_on_checkpoint`)
- WHEN the call lacks the explicit authorization capability
- THEN the function returns an unauthorized error before loading any checkpoint or performing inference

#### Scenario: Direct call to statistics function blocked
- GIVEN a direct call to the statistics computation function (e.g., `compute_metrics`)
- WHEN the call lacks the explicit authorization capability
- THEN the function returns an unauthorized error before accessing any evaluation results or producing statistics

### Requirement C-1: Non-Destructive Output Preservation (`overwrite=False`)
The system MUST preserve an existing valid output tree byte-for-byte when `overwrite=False` and publish new evaluations to a deterministic versioned path without partial replacement or temporary-file leakage.

#### Scenario: Existing valid output preserved
- GIVEN an existing output tree that matches the expected valid result structure and content
- AND the evaluation is invoked with `overwrite=False`
- WHEN the evaluation completes successfully
- THEN the existing output tree remains unchanged byte-for-byte
- AND the new evaluation results are written to a deterministic versioned subdirectory (e.g., `output/v<increment>/`)
- AND no temporary files are left in the output tree location after completion

#### Scenario: No temporary-file leakage
- GIVEN an evaluation run with `overwrite=False`
- WHEN the evaluation completes (success or failure)
- THEN no temporary files remain in the output directory tree that could cause partial visibility of results

#### Scenario: Versioned output path determinism
- GIVEN two evaluation runs with identical inputs, configuration, and timestamp granularity (to the second)
- WHEN each run completes successfully with `overwrite=False`
- THEN both outputs are written to the same versioned path (e.g., `output/v42/`) and are byte-for-byte identical

#### Scenario: Version allocation atomicity
- GIVEN multiple concurrent evaluation attempts with `overwrite=False`
- WHEN they complete
- THEN each receives a distinct versioned output path (e.g., `v42`, `v43`, `v44`) and no two writes occur to the same path simultaneously
- AND the version allocation is atomic such that no version is skipped or duplicated

### Requirement C-2: Controlled Overwrite Behavior (`overwrite=True`)
The system MUST preserve allowlisted-tree checks, atomic publication, manifest-last ordering, and restoration/rollback guarantees when `overwrite=True` is explicitly specified.

#### Scenario: Overwrite requires allowlisted existing tree
- GIVEN an existing output tree that is NOT in the allowlisted set (e.g., contains unexpected files or directories)
- AND the evaluation is invoked with `overwrite=True`
- WHEN the evaluation begins
- THEN the system rejects the operation and does not modify the existing tree

#### Scenario: Overwrite of allowlisted tree is atomic
- GIVEN an existing output tree that is in the allowlisted set
- AND the evaluation is invoked with `overwrite=True`
- WHEN the evaluation completes successfully
- THEN the previous tree is replaced atomically (e.g., via rename or transaction) such that observers never see a partially written state
- AND a restoration/rollback mechanism is available to revert to the pre-update state if needed

#### Scenario: Manifest-last ordering preserved
- GIVEN an evaluation run with `overwrite=True` that produces a new manifest file
- WHEN the evaluation completes
- THEN the manifest file is written last among all output files, ensuring that a partially present output tree without a manifest is treated as incomplete

### Requirement C-3: Truthful Evidence Reporting
The system MUST record focused remediation results truthfully and never represent the prior full-suite timeout as a pass or imply stronger validation than supported.

#### Scenario: Focused success reported as focused success
- GIVEN an evaluation run that passes all remediation-focused checks (A-1 through B-5) and completes successfully
- WHEN the evidence is recorded
- THEN the outcome is reported as a focused remediation success, with no claim that the full-suite validation passed

#### Scenario: Pre-existing timeout remains incomplete
- GIVEN the prior full-suite timeout evidence from incident #1793 and escalated review receipt `review-a81b3edbc82c5830`
- WHEN the evidence for the new evaluation is recorded
- THEN the prior timeout is explicitly labeled as incomplete evidence and is never converted to a pass or represented as successful validation

#### Scenario: Evidence distinguishes remediation from full suite
- GIVEN an evaluation run that completes the remediation-focused checks
- WHEN the evidence is recorded
- THEN the report clearly states that only the focused remediation checks were performed and passed, and that the full-suite evaluation remains incomplete due to timeout

### Non-Goals (Out of Scope)
The following are explicitly NOT goals of this remediation and must not be implemented or implied as part of this change:
- Accessing external cohort data (e.g., Kaggle, public ADNI/OASIS downloads)
- Performing network access in production evaluation paths
- Using GPU acceleration for evaluation or validation
- Creating or distributing evaluation notebooks
- Expanding the scientific feature set (e.g., new metrics, models, or analyses)
- Altering the review lifecycle or attempting to resolve incident #1793 or receipt `review-a81b3edbc82c5830`
- Performing Phase 17 work or planning
- Changing data preprocessing, partition schemes, or loss functions
- Validating scientific claims or producing manuscript-ready outputs