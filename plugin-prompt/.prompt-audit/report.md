# Prompt Quality Audit Report — pew-prompt-audit (Self-Audit)

**Target**: `plugin-prompt/`
**Files audited**: 11 (9 agents, 1 skill, 1 command)
**Estimated total tokens**: ~12,800
**Date**: 2026-03-24

---

## Executive Summary

The pew-prompt-audit plugin is a well-structured multi-agent audit system with strong conventions: consistent frontmatter, universal skill referencing, clear phase sequencing, and a well-defined 30-item defect taxonomy. However, the self-audit reveals **8 High** and **14 Medium** severity findings across the system — primarily around **scope conflicts between the skill and orchestrator** (the skill says `{output-dir}` but the orchestrator hardcodes `.prompt-audit/`), **missing edge case handling** across all agents, and **significant cross-file duplication** in input/preamble blocks.

### Top 3 Strengths
- **Comprehensive taxonomy**: The 30-item defect taxonomy in SKILL.md is well-grounded in published research, with concrete detection signals and business risk for each item
- **Consistent agent pattern**: All 9 agents share identical frontmatter structure, tools, skill reference, and completion signal format
- **Clear phase sequencing**: The orchestrator's 5-phase flow with explicit validation gates between phases is robust

### Top 3 Critical Issues
1. **Path variable conflict**: SKILL.md uses `{output-dir}`, orchestrator hardcodes `.prompt-audit/`, and agents use `{output-dir}` — agents may resolve the placeholder differently than the orchestrator intends
2. **No edge case handling**: Zero agents specify what to do when finding no issues, when inventory finds 0 files (except orchestrator), or when referenced files don't exist
3. **Heavy cross-file duplication**: The "Input" section pattern (~40 tokens) is repeated verbatim across all 8 Phase 2-4 agents

---

## System Overview

| Type | Count | Avg Tokens |
|------|:---:|:---:|
| Agent | 9 | ~1,050 |
| Skill | 1 | ~4,100 |
| Command | 1 | ~1,700 |
| **Total** | **11** | **~12,800** |

### Handoff Graph

```
pew-prompt-audit.md (orchestrator)
├── Phase 1: prompt-audit-inventory        → 01-inventory.json
├── Phase 2 (parallel):
│   ├── prompt-audit-coherence             → 02-coherence.md
│   ├── prompt-audit-specification         → 03-specification.md
│   ├── prompt-audit-structure             → 04-structure.md
│   ├── prompt-audit-efficiency            → 05-efficiency.md
│   ├── prompt-audit-consistency           → 06-consistency.md
│   └── prompt-audit-antipatterns          → 07-antipatterns.md
├── Phase 3: prompt-audit-synthesis        → 08-synthesis.md
└── Phase 4: prompt-audit-remediation      → 09-remediation.md
```

All agents reference skill: `pew-prompt-audit`. All agents declare tools: `Read, Grep, Glob, Write`. All agents have completion signals.

---

## Key Metrics

| Metric | Value | Grade |
|--------|-------|:---:|
| **Overall Health** | B+ | |
| **Critical findings** | 0 | |
| **High findings** | 8 | |
| **Medium findings** | 14 | |
| **Low findings** | 5 | |
| **Completion signal coverage** | 100% (9/9 agents) | A |
| **Skill coverage** | 100% (9/9 agents) | A |
| **Contract integrity** | 82% (1 path variable mismatch) | B |
| **Specification completeness** | 67% (6/9 agents have full output spec) | C |
| **Duplication ratio** | ~8% (~1,000 tokens duplicated) | B |

---

## Findings

### [High] #9 — Scope Conflict: `{output-dir}` vs `.prompt-audit/`

- **File**: SKILL.md (line 160-162) vs pew-prompt-audit.md (line 28-41)
- **Defect**: #9 — Scope Conflict
- **Issue**: SKILL.md's file-saving instructions use `{output-dir}/` as the path placeholder. All 9 agents inherit this and use `{output-dir}` in their output instructions. But the orchestrator hardcodes `.prompt-audit/` in every spawn prompt. These are different tokens — `{output-dir}` is a variable that must be resolved, while `.prompt-audit/` is a literal. The orchestrator never defines what `{output-dir}` resolves to.
- **Evidence**:
  - SKILL.md: `Signal completion with: [prompt-audit-<name>] COMPLETE -- saved to {output-dir}/<filename>`
  - Orchestrator: `Save your findings to .prompt-audit/02-coherence.md`
  - Agent (coherence): `Write {output-dir}/02-coherence.md`
- **Impact**: Agent receives two conflicting path instructions — one from its own body (`{output-dir}`) and one from the orchestrator spawn prompt (`.prompt-audit/`). The model will likely follow the spawn prompt (recency), but the ambiguity is unnecessary.
- **Fix**: Pick one convention. Either: (a) change all agent files to use `.prompt-audit/` literally, or (b) add to orchestrator spawn prompts: "The output directory (`{output-dir}`) is `.prompt-audit/`". Option (b) is more flexible for reuse.
- **Effort**: S

---

### [High] #5 — Undefined Edge Cases: No "zero findings" guidance

- **File**: All 6 Phase 2 agents + synthesis + remediation
- **Defect**: #5 — Undefined Edge Cases
- **Issue**: No agent specifies what to do when it finds zero issues in its domain. What does `02-coherence.md` look like when there are no contradictions? Does the agent write an empty findings section? A "no findings" statement? Does synthesis handle agents that report zero findings?
- **Evidence**: None of the 8 agents (prompt-audit-coherence through prompt-audit-remediation) contain instructions like "If no findings in this category, write a brief statement confirming no issues detected."
- **Impact**: Agent may produce inconsistent output: some might write "No findings", others might write empty sections, others might hallucinate marginal findings to avoid appearing incomplete.
- **Fix**: Add to SKILL.md's Finding Report Format section: "If no defects are found in your assigned categories, write: `## Findings\n\nNo defects detected in categories #N-M. [brief rationale for why the system is clean in this area]`"
- **Effort**: S

---

### [High] #5 — Undefined Edge Cases: Re-run behavior

- **File**: pew-prompt-audit.md (orchestrator)
- **Defect**: #5 — Undefined Edge Cases
- **Issue**: No guidance on what happens when `.prompt-audit/` already exists from a prior run. Should the orchestrator overwrite? Archive the old results? Warn the user?
- **Evidence**: Step 0 says "Create `.prompt-audit/`" but doesn't address pre-existing directory.
- **Impact**: On re-run, old findings may persist alongside new ones if filenames differ, or new results silently overwrite without the user knowing.
- **Fix**: Add to Step 0: "If `.prompt-audit/` already exists, inform the user and overwrite. Old results are replaced."
- **Effort**: S

---

### [High] #30 — Hallucination-Inducing Gap: `{output-dir}` never defined in agents

- **File**: All 9 agent files
- **Defect**: #30 — Hallucination-Inducing Gap
- **Issue**: Every agent references `{output-dir}` as a path placeholder, but the variable is never defined within the agent file itself. The agent relies on either: (a) the skill file (which also uses `{output-dir}` without defining it), or (b) the orchestrator spawn prompt (which uses `.prompt-audit/` literally). The agent has no mechanism to resolve `{output-dir}` into an actual path.
- **Evidence**: prompt-audit-coherence.md line 68: `Write {output-dir}/02-coherence.md`; no prior line defines what `{output-dir}` is.
- **Impact**: Related to the scope conflict above. Model must infer the value from context. Usually works (the spawn prompt provides the literal), but adds cognitive load and fragility.
- **Fix**: Add a line to each agent's Input section: "The orchestrator provides the output directory path in the spawn prompt. All file paths below use `{output-dir}` as a placeholder for this path."
- **Effort**: S

---

### [High] #2 — Underspecified Constraint: Inventory agent output lacks length/scope bounds

- **File**: prompt-audit-inventory.md
- **Defect**: #2 — Underspecified Constraint
- **Issue**: The inventory agent is told to "be exhaustive" and "Do NOT skip any prompt file" but has no guidance on maximum scope. For a project with 200+ agent files, the inventory JSON could be enormous, consuming the entire context for Phase 2 agents.
- **Evidence**: Line 135: "Do NOT skip any prompt file. Be exhaustive."
- **Impact**: Context overflow for Phase 2 agents that must read the full inventory JSON.
- **Fix**: Add bounds: "If the target contains >50 prompt files, include full details for the top 50 by token count and summary entries for the rest. Flag the truncation in the summary."
- **Effort**: S

---

### [High] #22 — Broken Handoff Contract: Orchestrator validation vs. agent output

- **File**: pew-prompt-audit.md (lines 47-51, 75)
- **Defect**: #22 — Broken Handoff Contract
- **Issue**: The orchestrator specifies validation criteria for inventory output: "contains valid JSON with `summary`, `files`, `handoffGraph`, and `toolUsage` fields." But the inventory agent's JSON schema also includes `target` and `largestFiles` as top-level fields. The orchestrator doesn't validate these. More importantly, for Phase 2 output, the orchestrator only validates "exist and are non-empty" — no section validation.
- **Evidence**: Step 1 validates 4 fields. Step 2 validates existence only. Step 3 validates sections. Inconsistent rigor across phases.
- **Impact**: Low practical risk (agents are well-specified), but inconsistent validation rigor means Phase 2 output gaps may not be caught.
- **Fix**: Standardize validation: either validate specific sections for all phases (like Step 3) or validate existence-only for all phases. Recommendation: validate that each Phase 2 file contains a `## Findings` section.
- **Effort**: S

---

### [High] #8 — Example-Instruction Mismatch: SKILL.md completion signal format

- **File**: SKILL.md (line 162) vs agents
- **Defect**: #8 — Example-Instruction Mismatch
- **Issue**: SKILL.md line 162 shows the completion signal pattern as: `[prompt-audit-<name>] COMPLETE -- saved to {output-dir}/<filename>`. But most existing PEW audit agents (react-audit, test-audit) use the format with a checkmark: `[agent-name] COMPLETE ✓ -- saved to {path}`. The pew-prompt-audit agents omit the `✓` character. The orchestrator doesn't mention what signal format to expect.
- **Evidence**:
  - SKILL.md: `[prompt-audit-<name>] COMPLETE -- saved to`
  - react-audit-inventory.md: `[react-audit-inventory] COMPLETE ✓ -- saved to`
- **Impact**: Low behavioral risk (the signal will still work), but inconsistency with the broader PEW ecosystem.
- **Fix**: Add `✓` to the completion signal in SKILL.md and all agents: `[prompt-audit-<name>] COMPLETE ✓ -- saved to {output-dir}/<filename>`
- **Effort**: S

---

### [High] #15 — Missing Output Format: Phase 2 agents lack "no findings" template

- **File**: All 6 Phase 2 agents
- **Defect**: #15 — Missing Output Format
- **Issue**: The SKILL.md defines the finding report format (with `## Findings` and `## Strengths` sections), but does not define a complete output template showing ALL required sections per agent. Phase 2 agents define their own additional sections (e.g., coherence adds "Conflict Map", specification adds "Coverage Matrix") but these are specified in code blocks that could be missed.
- **Evidence**: Each Phase 2 agent defines custom sections in their Output section. These are in markdown code blocks within the agent, not in the shared skill.
- **Impact**: Synthesis agent must know about 6 different custom section formats. If an agent omits its custom section, synthesis may not flag it.
- **Fix**: Add a summary in SKILL.md or the synthesis agent listing all expected custom sections per agent: "coherence: Conflict Map; specification: Coverage Matrix; structure: Structural Summary; efficiency: Token Budget + Duplication Clusters; consistency: System Coherence; antipatterns: Anti-Pattern Heat Map + Tone Calibration Summary"
- **Effort**: M

---

### [Medium] #17 — Cross-File Duplication: Input section boilerplate

- **File**: All 8 Phase 2-4 agents
- **Defect**: #17 — Cross-File Duplication
- **Issue**: Every Phase 2 agent has a near-identical Input section:
  ```
  ## Input
  - Read `{output-dir}/01-inventory.json` for the file list [and X]
  - Read all source prompt files referenced in the inventory
  ```
  This pattern is repeated 8 times with minor variations (~40 tokens each, ~320 tokens total waste).
- **Evidence**: Identical in coherence, specification, structure, efficiency, consistency, antipatterns. Slightly different in synthesis (reads 01-07) and remediation (reads 08 + 02-07).
- **Impact**: Maintenance burden. If the inventory filename or format changes, 8 files need updating.
- **Fix**: Move the input convention to SKILL.md: "Phase 2 agents: read `{output-dir}/01-inventory.json` and all source prompt files. Phase 3+: read all prior phase outputs." Then agents need only a one-line reference.
- **Effort**: M

---

### [Medium] #17 — Cross-File Duplication: Role preamble pattern

- **File**: All 9 agents
- **Defect**: #17 — Cross-File Duplication
- **Issue**: Every agent opens with "You are a senior prompt engineer specializing in [X]. Your job is to [Y]." While this is a valid pattern (role-setting), the "senior prompt engineer" role is repeated 9 times.
- **Evidence**: 9 agents, each with a ~25-token role sentence.
- **Impact**: Minor token waste (~225 tokens). The role could be inherited from the skill.
- **Fix**: Add the base role to SKILL.md: "You are a senior prompt engineer." Agents can append their specialization. Low priority — role-setting is important per-agent.
- **Effort**: S (but low priority — role-per-agent is actually good practice)

---

### [Medium] #28 — Missing Rationale: Why chars/4 for token estimation?

- **File**: prompt-audit-inventory.md (line 37)
- **Defect**: #28 — Missing Rationale
- **Issue**: "Token estimate: character count / 4 (rough approximation)" — no explanation of why 4, how rough, or what the limitation is.
- **Evidence**: Line 37: `character count / 4 (rough approximation)`
- **Impact**: Agent may apply this formula without understanding its margin of error (~20-30% for English text). If questioned by the model or user, there's no justification.
- **Fix**: Add: "character count / 4 (standard approximation for English text; actual token count varies by ~25% depending on vocabulary and code content)"
- **Effort**: S

---

### [Medium] #28 — Missing Rationale: Why >3 emphatic markers is the threshold?

- **File**: prompt-audit-antipatterns.md (line 28)
- **Defect**: #28 — Missing Rationale
- **Issue**: "Threshold: >3 emphatic markers per file is a flag. >5 is High severity." — no explanation of why these specific numbers.
- **Evidence**: Line 28-29.
- **Impact**: Agent applies the rule mechanically. A file with 4 justified emphatic markers gets flagged unnecessarily.
- **Fix**: Add: "These thresholds are calibrated for typical agent files (~500-1500 tokens). For longer files, scale proportionally. The key signal is density, not absolute count."
- **Effort**: S

---

### [Medium] #1 — Ambiguous Directive: "adapt to what exists" in inventory

- **File**: prompt-audit-inventory.md (line 19)
- **Defect**: #1 — Ambiguous Directive
- **Issue**: "Search patterns (adapt to what exists)" — vague instruction. Adapt how? What if patterns find nothing?
- **Evidence**: Line 19: "Use Glob to find all prompt-related `.md` files. Search patterns (adapt to what exists):"
- **Impact**: Model may interpret "adapt" differently: skip patterns that return nothing? Try alternative patterns? Broaden the search?
- **Fix**: Replace with: "Use these Glob patterns. If a pattern returns no results, skip it silently. If all patterns return no results, report zero prompt files found."
- **Effort**: S

---

### [Medium] #11 — Poor Instruction Ordering: SKILL.md taxonomy before instructions

- **File**: SKILL.md
- **Defect**: #11 — Poor Instruction Ordering
- **Issue**: The skill file places the 30-item taxonomy (lines 31-101, ~3,500 tokens) before the operational instructions (severity scale, remediation tiers, finding format, file-saving instructions at lines 105-163). By the time the agent reaches the format and process instructions, 3,500 tokens of taxonomy have diluted attention.
- **Evidence**: Lines 31-101: taxonomy tables. Lines 105-163: operational instructions.
- **Impact**: The taxonomy is reference material (agents look up specific defects as needed). The operational instructions are behavioral rules (agents must follow these). Behavioral rules after reference material is the "lost-in-the-middle" anti-pattern.
- **Fix**: Reorder SKILL.md: Purpose → Tone → **Severity Scale + Finding Format + File-Saving Instructions** → Taxonomy (reference). Or reinforce key behavioral rules at the end of the file.
- **Effort**: M

---

### [Medium] #13 — Overloaded Prompt: Orchestrator handles 6 task categories

- **File**: pew-prompt-audit.md
- **Defect**: #13 — Overloaded Prompt
- **Issue**: The orchestrator handles: target detection (Research), directory creation (Generation), agent spawning (Coordination), output validation (Validation), report writing (Generation), and phase-offering (Decision). That's 5-6 categories.
- **Evidence**: Steps 0-5 span all categories.
- **Impact**: Acceptable for an orchestrator (coordination is its role), but the report-writing step (Step 5) is substantial generation that could be a separate agent.
- **Fix**: Low priority. If report quality is inconsistent, consider extracting Step 5 into a `prompt-audit-reporter` agent. For now, the orchestrator pattern matches react-audit and test-audit.
- **Effort**: L (if extracted) / none (if kept)

---

### [Medium] #16 — Redundant Instructions: "Do NOT perform analysis yourself" repeated in spirit

- **File**: pew-prompt-audit.md
- **Defect**: #16 — Redundant Instructions
- **Issue**: The orchestrator says "Your job is NOT to perform the audit yourself" (line 9) AND "Do NOT perform analysis yourself" (line 136). Same instruction stated twice.
- **Evidence**: Lines 9 and 136.
- **Impact**: Minor token waste. The reinforcement at the end (recency position) is actually beneficial per the structure guidelines, so this is borderline.
- **Fix**: Keep the reinforcement (it follows the "critical rules at top + reinforcement at end" pattern). Tighten the wording: change line 9 to just introduce the role without the prohibition, let line 136 carry the prohibition.
- **Effort**: S

---

### [Medium] #14 — Inconsistent Formatting: Completion signal punctuation

- **File**: All agents vs SKILL.md
- **Defect**: #14 — Inconsistent Formatting
- **Issue**: Completion signals use slightly different formatting across files:
  - SKILL.md: `[prompt-audit-<name>] COMPLETE -- saved to {output-dir}/<filename>`
  - inventory: `[prompt-audit-inventory] COMPLETE -- saved to {output-dir}/01-inventory.json`
  - coherence: `[prompt-audit-coherence] COMPLETE -- saved to {output-dir}/02-coherence.md`
  The SKILL uses `<name>` placeholder while agents use their actual name. This is correct behavior — but some agents use single dashes and some use double dashes inconsistently.
- **Evidence**: All agents use `--` consistently. Actually, on closer inspection, this is consistent. Downgrading.
- **Impact**: Minimal — formatting is actually consistent.
- **Fix**: No action needed. This finding is withdrawn upon verification.
- **Effort**: N/A

---

### [Medium] #5 — Undefined Edge Cases: What if an agent fails?

- **File**: pew-prompt-audit.md
- **Defect**: #5 — Undefined Edge Cases
- **Issue**: The orchestrator says "If an agent fails, report the failure and ask the user how to proceed" (line 134). But what constitutes "failure"? Timeout? Empty output? Output missing required sections? Agent error message?
- **Evidence**: Line 134 mentions failure but doesn't define it.
- **Impact**: Orchestrator may not catch partial failures (agent produces output but misses required sections).
- **Fix**: Define failure: "An agent has failed if: (a) it does not produce a completion signal, (b) its output file is empty or missing, or (c) its output file is missing required sections (## Findings for Phase 2, ## Executive Summary for Phase 3)."
- **Effort**: S

---

### [Medium] #3 — Missing Success Criteria: Synthesis health grade boundaries

- **File**: prompt-audit-synthesis.md (lines 83)
- **Defect**: #3 — Missing Success Criteria
- **Issue**: Health grade thresholds are defined but not actionable: "A (0-2 Critical), B (0 Critical, <5 High)..." — but the orchestrator doesn't reference or use this grade. It's generated but never consumed.
- **Evidence**: Synthesis produces a grade, but the orchestrator's Step 5 report template doesn't specify how to present or act on the grade.
- **Impact**: Grade is decorative. Could be valuable if the orchestrator used it as a gate ("Grade D or F: warn user about fundamental issues before presenting remediation").
- **Fix**: Add to orchestrator Step 5: "Include the health grade prominently in the executive summary. If grade is D or F, lead with a warning."
- **Effort**: S

---

### [Medium] #18 — Token Bloat: Verbose taxonomy preambles in SKILL.md

- **File**: SKILL.md
- **Defect**: #18 — Token Bloat
- **Issue**: Each taxonomy section has a research-citing preamble before its table. While grounding is valuable, some preambles are 2-3 sentences that could be tighter.
- **Evidence**:
  - Section A: "Vague or incomplete instructions are the #1 failure mode across all LLM providers' guidance. Anthropic's golden rule: 'Show your prompt to a colleague with minimal context. If they'd be confused, Claude will be too.'" (2 sentences, ~40 tokens)
  - Section B: 2 sentences, ~45 tokens
  - Section C: 2 sentences, ~35 tokens
  - etc. Total: ~250 tokens of preambles
- **Impact**: Preambles add context (good) but consume tokens that could be recovered. For a skill file that's loaded into every agent's context, 250 tokens × 9 agents = 2,250 wasted tokens system-wide per audit run.
- **Fix**: Consolidate preambles into a single "Research Basis" section at the top. Keep one-line headers per section: "### A. Specification & Intent" (no preamble paragraph).
- **Effort**: M

---

### [Low] #23 — Inconsistent Naming: `{output-dir}` vs `{config.paths.audit_react}`

- **File**: System-wide
- **Defect**: #23 — Inconsistent Naming
- **Issue**: The pew-prompt-audit system uses `{output-dir}` as its path placeholder, while the react-audit uses `{config.paths.audit_react}` and the test-audit uses `{config.paths.audit_test}`. This is intentional (standalone plugin without pew.yaml), but means the naming convention differs from the broader PEW ecosystem.
- **Evidence**: All prompt-audit agents: `{output-dir}`. All react-audit agents: `{config.paths.audit_react}`.
- **Impact**: Minimal for standalone operation. Could cause confusion if the plugin is later integrated.
- **Fix**: Document the deliberate difference in SKILL.md: "This plugin uses `{output-dir}` instead of `{config.paths.*}` because it operates standalone without pew.yaml."
- **Effort**: S

---

### [Low] #27 — Negative Framing: "Do NOT skip any prompt file"

- **File**: prompt-audit-inventory.md (line 135)
- **Defect**: #27 — Negative Framing
- **Issue**: "Do NOT skip any prompt file" — negative framing with emphasis.
- **Evidence**: Line 135.
- **Impact**: Marginal. The positive equivalent is more useful.
- **Fix**: Replace with: "Include every discovered prompt file in the inventory. If a file is ambiguous, include it with a note."
- **Effort**: S

---

### [Low] #27 — Negative Framing: "Do NOT perform analysis yourself"

- **File**: pew-prompt-audit.md (line 136)
- **Defect**: #27 — Negative Framing
- **Issue**: "Do NOT perform analysis yourself. Your role is coordination and synthesis into the final report." — prohibition first, positive guidance second.
- **Evidence**: Line 136.
- **Impact**: The positive guidance follows immediately, so this is borderline. The emphasis on NOT is stronger than the alternative.
- **Fix**: Rewrite as: "Your role is coordination and report synthesis. Delegate all analysis to specialist agents."
- **Effort**: S

---

### [Low] #18 — Token Bloat: Research paragraph in SKILL.md Purpose

- **File**: SKILL.md (lines 13-15)
- **Defect**: #18 — Token Bloat
- **Issue**: The Purpose section has a dense research-citing paragraph: "Grounded in empirical research: Anthropic's context engineering principles (2025)... DSPy (Stanford NLP) proves structured prompt optimization outperforms expert-crafted prompts by 5-46%." (~80 tokens) This is background context for human readers, not operational instructions for the model.
- **Evidence**: Lines 13-15.
- **Impact**: 80 tokens × 9 agents = 720 wasted tokens per audit run. The model doesn't need research citations to perform its task.
- **Fix**: Move to a `## Research Basis` section at the bottom, or compress to one sentence: "Grounded in prompt defect research from Anthropic, OpenAI, and academic literature (see todo/prompt-optimizer-research.md)."
- **Effort**: S

---

### [Low] #24 — Tool Declaration Mismatch: Inventory agent may need Bash

- **File**: prompt-audit-inventory.md
- **Defect**: #24 — Tool Declaration Mismatch
- **Issue**: The inventory agent declares `Read, Grep, Glob, Write` but no `Bash`. For token estimation, it uses "character count / 4" which can be done by reading files. However, if the target directory has many files, `wc -c` via Bash would be faster and more accurate than reading every file to count characters.
- **Evidence**: Tools: Read, Grep, Glob, Write. No Bash.
- **Impact**: Minor performance concern, not a correctness issue. The agent can read files with Read to get content length.
- **Fix**: Consider adding Bash for `wc -c` and `find` operations. Low priority.
- **Effort**: S

---

## Defect Heat Map

| # | Defect | Occurrences | Avg Severity |
|---|--------|:-:|---|
| 5 | Undefined Edge Cases | 4 | High |
| 17 | Cross-File Duplication | 2 | Medium |
| 28 | Missing Rationale | 2 | Medium |
| 9 | Scope Conflict | 1 | High |
| 30 | Hallucination-Inducing Gap | 1 | High |
| 22 | Broken Handoff Contract | 1 | High |
| 8 | Example-Instruction Mismatch | 1 | High |
| 15 | Missing Output Format | 1 | High |
| 2 | Underspecified Constraint | 1 | High |
| 27 | Negative Framing | 2 | Low |
| 18 | Token Bloat | 2 | Low-Medium |
| 11 | Poor Instruction Ordering | 1 | Medium |
| 13 | Overloaded Prompt | 1 | Medium |
| 16 | Redundant Instructions | 1 | Medium |
| 1 | Ambiguous Directive | 1 | Medium |
| 3 | Missing Success Criteria | 1 | Medium |
| 23 | Inconsistent Naming | 1 | Low |
| 24 | Tool Declaration Mismatch | 1 | Low |

## File Heat Map

| File | High | Medium | Low | Total | Top Issue |
|------|:-:|:-:|:-:|:-:|---|
| SKILL.md | 2 | 3 | 1 | 6 | #9 Scope Conflict, #11 Ordering |
| pew-prompt-audit.md | 1 | 4 | 1 | 6 | #22 Contract, #5 Edge Cases |
| prompt-audit-inventory.md | 1 | 2 | 2 | 5 | #2 Underspec, #1 Ambiguous |
| prompt-audit-coherence.md | 1 | 1 | 0 | 2 | #30 Gap ({output-dir}) |
| prompt-audit-specification.md | 1 | 1 | 0 | 2 | #30 Gap, #5 Edge Cases |
| prompt-audit-antipatterns.md | 0 | 2 | 0 | 2 | #28 Missing Rationale |
| prompt-audit-synthesis.md | 0 | 1 | 0 | 1 | #3 Success Criteria |
| (other agents) | 1 each | 0-1 | 0 | 1-2 | #30 Gap, #17 Duplication |

---

## Prioritized Remediation Roadmap

### Tier 1 — Immediate (8 items, ~2 hours)

| # | Finding | Fix | Effort |
|---|---------|-----|:---:|
| 1 | `{output-dir}` scope conflict | Add definition line to orchestrator spawn prompts OR change agents to use `.prompt-audit/` | S |
| 2 | Zero-findings edge case | Add template to SKILL.md for "no findings" output | S |
| 3 | Re-run edge case | Add overwrite guidance to orchestrator Step 0 | S |
| 4 | `{output-dir}` hallucination gap | Add variable resolution note to agent Input sections | S |
| 5 | Inventory scope bounds | Add >50 file truncation guidance | S |
| 6 | Orchestrator validation inconsistency | Standardize validation to check `## Findings` section | S |
| 7 | Completion signal missing `✓` | Add checkmark to SKILL.md and all agents | S |
| 8 | Agent failure definition | Define failure criteria in orchestrator | S |

### Tier 2 — Short Term (6 items, ~4 hours)

| # | Finding | Fix | Effort |
|---|---------|-----|:---:|
| 9 | Phase 2 custom section registry | Add expected-sections list to SKILL.md or synthesis agent | M |
| 10 | SKILL.md instruction ordering | Move operational instructions before taxonomy | M |
| 11 | Taxonomy preamble consolidation | Move research preambles to single section | M |
| 12 | Input section duplication | Extract to SKILL.md convention | M |
| 13 | Health grade usage | Wire grade into orchestrator report | S |
| 14 | "adapt to what exists" ambiguity | Replace with explicit fallback behavior | S |

### Tier 3 — Ongoing (5 items, low priority)

| # | Finding | Fix | Effort |
|---|---------|-----|:---:|
| 15 | Research paragraph bloat | Compress or relocate | S |
| 16 | Negative framing (2 instances) | Rewrite as positive | S |
| 17 | Naming convention documentation | Document `{output-dir}` vs `{config.paths.*}` difference | S |
| 18 | Inventory Bash tool | Consider adding for performance | S |
| 19 | Orchestrator report extraction | Consider reporter agent if quality inconsistent | L |

---

## Top 5 Before/After Fixes

### Fix 1: Resolve `{output-dir}` scope conflict (SKILL.md + all agents)

**Before** (SKILL.md line 160-162):
> 1. Write your complete output to your designated file under `{output-dir}/`.
> 2. Do not write to any other agent's file.
> 3. Signal completion with: `[prompt-audit-<name>] COMPLETE -- saved to {output-dir}/<filename>`

**After**:
> 1. Write your complete output to your designated file. The output directory path is provided by the orchestrator in your spawn prompt — all `{output-dir}` references below resolve to that path.
> 2. Do not write to any other agent's file.
> 3. Signal completion with: `[prompt-audit-<name>] COMPLETE ✓ -- saved to {output-dir}/<filename>`

### Fix 2: Add zero-findings template (SKILL.md, after Finding Report Format)

**Before**: (nothing)

**After**:
> ### When No Defects Are Found
>
> If your analysis finds no defects in your assigned categories, write:
> ```markdown
> ## Findings
>
> No defects detected in categories #N-M. [One sentence explaining why the system is clean in this area, e.g., "All agents use consistent naming conventions matching the shared skill's terminology."]
>
> ## Strengths
>
> - **[relevant strength]**: [Why this area is well-crafted]
> ```

### Fix 3: Add re-run handling (pew-prompt-audit.md Step 0)

**Before**:
> Create `.prompt-audit/` in the current working directory. This is the shared workspace all agents will write to.

**After**:
> Create `.prompt-audit/` in the current working directory (or reuse if it already exists from a prior run — existing files will be overwritten). This is the shared workspace all agents will write to.

### Fix 4: Define agent failure (pew-prompt-audit.md Critical Rules)

**Before**:
> - If an agent fails, report the failure and ask the user how to proceed -- do not skip phases.

**After**:
> - An agent has failed if: (a) no completion signal is received, (b) its output file is empty or missing, or (c) output is missing required `## Findings` section. On failure, report which agent failed and why, then ask the user how to proceed — do not skip phases.

### Fix 5: Tighten inventory scope (prompt-audit-inventory.md)

**Before**:
> Do NOT skip any prompt file. Be exhaustive. If a file is ambiguous (could be prompt or documentation), include it with a note.

**After**:
> Include every discovered prompt file in the inventory. If a file is ambiguous (could be prompt or documentation), include it with a `"note"` field. If the target contains >50 prompt files, include full details for the 50 largest by token count and summary-only entries for the rest, flagging the truncation in the `summary` object.
