<!--
  SYNC IMPACT REPORT
  Version Change: [template] → 1.0.0
  
  Modified Principles:
    - NEW: I. Correctness & Determinism
    - NEW: II. Explainability & Traceability
    - NEW: III. Layout-First Processing
    - NEW: IV. Modular Pipeline Architecture
    - NEW: V. Testing & Validation
    - NEW: VI. Explicit Failure Handling
    - NEW: VII. Performance & Scalability
  
  Added Sections:
    - Core Principles (all 7 principles)
    - Code Quality Standards
    - Testing Requirements
    - Development Workflow
    - Governance
  
  Removed Sections:
    - None (initial constitution)
  
  Templates Status:
    ✅ plan-template.md - Constitution Check section ready
    ✅ spec-template.md - User story and acceptance criteria format aligned
    ✅ tasks-template.md - Testing phases and validation tasks compatible
    ✅ checklist-template.md - Compatible with validation requirements
    ✅ agent-file-template.md - No updates required
  
  Follow-up TODOs:
    - None (all core principles defined)
  
  Commit Message:
    docs: establish DeBleed constitution v1.0.0 (initial governance framework)
-->

# DeBleed Constitution

## Core Principles

### I. Correctness & Determinism

The system MUST be deterministic and reproducible. Given the same input image, the system MUST
always produce the same output. This principle is NON-NEGOTIABLE.

- No hidden state, randomness, or non-deterministic behavior is allowed in the core pipeline.
- All processing steps must be repeatable and verifiable.
- Configuration changes that affect output must be explicit and version-controlled.

**Rationale**: Document processing requires absolute reliability. Users must trust that the same
scan processed today and tomorrow will yield identical results. Non-determinism makes debugging
impossible and undermines trust in the system.

### II. Explainability & Traceability

Image preprocessing and page detection MUST rely on explainable, deterministic techniques
(geometric analysis, connected components, text density heuristics) before introducing machine
learning approaches.

- All preprocessing decisions must have documented rationale and measurable impact.
- Magic numbers and thresholds must be centralized, configurable, and justified.
- Any future ML-based components must be optional, well-isolated, and measurable against
  baseline heuristic methods.

**Rationale**: When processing fails or produces unexpected results, developers and users must
be able to understand why. Explainable techniques enable systematic improvement and debugging.

### III. Layout-First Processing

The system MUST treat each scanned image as a potentially multi-page layout and MUST explicitly
identify the primary page region before performing OCR. No text extraction may occur on
unverified or secondary regions.

- Page detection and region selection is mandatory before OCR.
- The system must differentiate between primary content pages and secondary elements
  (gutters, margins, bleed, facing pages).
- When the primary page region cannot be confidently determined, the system must surface this
  explicitly instead of guessing.

**Rationale**: Extracting text from incorrect regions (margins, adjacent pages, gutters)
degrades output quality. Explicit region selection ensures only intended content is processed.

### IV. Modular Pipeline Architecture

The project favors clear, modular pipeline stages (preprocessing, layout detection, region
selection, OCR, output generation), each with well-defined inputs and outputs.

- Each pipeline stage must have a single, clear responsibility.
- Stages must be independently testable without requiring full pipeline execution.
- Data contracts between stages must be explicit and versioned.
- Changes to one stage must not require changes to other stages unless the contract changes.

**Rationale**: Modularity enables parallel development, isolated testing, and incremental
improvement. Well-defined interfaces allow components to evolve independently.

### V. Testing & Validation

All core logic must be unit-testable without requiring OCR execution. Layout detection and
preprocessing decisions must be validated using representative real-world scans.

- Unit tests must validate logic independently of external OCR services.
- Layout detection must be validated against real-world scan samples (partial pages, gutter
  inclusion, skewed scans, varied resolutions).
- Edge case coverage is mandatory: partial pages, gutter inclusion, skewed scans, multi-column
  layouts, margin notes.
- Regression tests must ensure that layout changes do not degrade existing results.

**Rationale**: Testing without OCR dependencies enables fast iteration and deterministic
validation. Real-world samples catch failures that synthetic test data misses.

### VI. Explicit Failure Handling

The tool must behave predictably and fail explicitly. When the system cannot proceed with
confidence, it must surface errors clearly rather than producing incorrect output.

- Failures must be reported with actionable diagnostic information.
- When the primary page region cannot be confidently determined, the system must report this
  instead of guessing.
- Output quality metrics (confidence scores, detected layout properties) should be surfaced
  to users when available.

**Rationale**: Silent failures and incorrect guesses erode trust. Explicit errors enable users
to understand and address issues, while incorrect silent output may go unnoticed until later
stages.

### VII. Performance & Scalability

The system must be able to process multi-page documents efficiently without loading the entire
document into memory. Preprocessing must remain lightweight and suitable for batch processing.

- Memory usage must scale linearly with single-page size, not total document size.
- Batch processing must support parallelization where possible.
- Processing overhead (preprocessing, layout detection) must be justified and measurable.

**Rationale**: Real-world book scans contain hundreds or thousands of pages. In-memory
processing of entire documents is impractical and limits scalability.

## Code Quality Standards

All code contributions must meet these quality requirements:

- **Unit Testing**: All core logic must be unit-testable without requiring OCR execution or
  external service dependencies.
- **Documentation**: Image processing steps must document their intent (what they do) and
  expected impact (why they do it).
- **Configuration**: Magic numbers and thresholds must be centralized (in a config module or
  file) and configurable. Hard-coded thresholds in implementation logic are prohibited.
- **Type Safety**: Use type hints (Python) or equivalent type annotations to document
  contracts and enable static analysis.

## Testing Requirements

All features and changes must include appropriate test coverage:

- **Layout Detection Validation**: Layout detection changes must be validated using
  representative real-world scans. Test suite must include edge cases: partial pages, gutter
  inclusion, skewed scans, multi-column layouts, margin notes.
- **Regression Testing**: Changes to preprocessing or layout detection must not degrade
  existing validated results. Baseline outputs must be maintained for comparison.
- **Contract Testing**: Pipeline stage interfaces must have contract tests ensuring output
  format and data integrity.
- **Performance Testing**: Changes affecting batch processing or memory usage must include
  performance benchmarks.

## Development Workflow

- **Feature Specifications**: All features begin with a written specification documenting user
  scenarios, requirements, and acceptance criteria (see [.specify/templates/spec-template.md](.specify/templates/spec-template.md)).
- **Implementation Planning**: Features require implementation plans documenting technical
  approach, pipeline integration, and testing strategy (see
  [.specify/templates/plan-template.md](.specify/templates/plan-template.md)).
- **Constitution Compliance**: All implementation plans must include a Constitution Check
  section verifying compliance with core principles. Non-compliance must be explicitly
  justified and documented.
- **Test-Driven Development**: For logic-heavy components (layout detection, preprocessing),
  tests should be written before implementation where practical.

## Governance

This constitution supersedes all other development practices and defines the non-negotiable
rules for the DeBleed project.

- **Amendments**: Constitution changes require documentation of the amendment rationale,
  version increment (following semantic versioning), and migration plan if existing code is
  affected.
- **Version Semantics**:
  - MAJOR: Backward incompatible principle removals or redefinitions.
  - MINOR: New principle/section added or materially expanded guidance.
  - PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
- **Compliance Verification**: All feature specifications, implementation plans, and code
  reviews must verify compliance with constitutional principles.
- **Justification Required**: Any deviation from constitutional principles must include
  explicit written justification in the relevant specification or plan document.

**Version**: 1.0.0 | **Ratified**: 2026-01-17 | **Last Amended**: 2026-01-17
