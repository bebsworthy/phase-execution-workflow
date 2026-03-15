# Phase BRD: <Phase Title>

status: not_started
phase_key: <phase-name>
phase_number: <N>
last_updated: YYYY-MM-DD

## 1. Context Intake

| Source | Relevance | Notes |
| ------ | --------- | ----- |

## 2. Problem Statement

## 3. Goals and Non-Goals

## 4. Scope Definition

## 5. Functional Capability Contract

<!-- Every FC MUST have at least one "Not Allowed" entry. If genuinely unrestricted, state "No restrictions identified" with rationale. -->

| FC ID | Actor | Preconditions | User Action | System Response | Not Allowed | Error Mapping | Evidence Target |
| ----- | ----- | ------------- | ----------- | --------------- | ----------- | ------------- | --------------- |

## 6. User Can / User Cannot

## 7. E2E User Test Flows

<!-- Required if phase has frontend tag or BRD contains "User can" -->

## 8. Acceptance Criteria

<!-- Every AC must reference specific FC(s) in "Covers FC". If an AC uses codebase-wide validation (e.g., grep across all files), FCs must collectively cover all affected files — or narrow the AC's Validation Signal to match the FC scope. -->

| AC ID | Covers FC | Criterion | Validation Signal |
| ----- | --------- | --------- | ----------------- |

## 9. Risks and Open Questions

| ID  | Type | Description | Mitigation | Status |
| --- | ---- | ----------- | ---------- | ------ |

---

Instructions: See SKILL.md Step 2 for authoring rules. FC rows must be atomic capability contracts. E2E flows required for user-facing phases. Run verify-traceability before advancing.
