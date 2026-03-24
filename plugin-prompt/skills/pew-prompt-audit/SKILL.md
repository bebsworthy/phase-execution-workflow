---
name: pew-prompt-audit
description: >
  Shared prompt defect taxonomy, severity scales, and output format for prompt audit agents.
  This skill is preloaded by all prompt-audit-* agents to ensure consistent evaluation criteria.
user-invocable: true
---

# Prompt Quality Audit Framework

## Purpose

This framework powers a multi-phase audit of LLM prompt systems -- agent definitions, skill files, command orchestrators, and project instructions (CLAUDE.md). It evaluates prompt clarity, coherence, structural health, token efficiency, cross-agent consistency, and adherence to provider best practices.

Grounded in prompt defect research from Anthropic (context engineering, 2025), OpenAI (GPT-4.1 prompting guide), Google DeepMind (OPRO), and academic literature (arxiv:2509.14404 — taxonomy of prompt defects). See `todo/prompt-optimizer-research.md` for full citations.

Every finding must answer: "What concrete harm does this cause -- incorrect agent behavior, wasted tokens, broken workflows, or inconsistent outputs?"

## Tone & Approach

- Direct and precise. Do not soften findings.
- Every finding must cite a specific defect number and include an actionable fix.
- **Call out strengths**: Note well-crafted prompts, not just problems.
- Prioritize by behavioral impact -- contradictions and broken contracts before style issues.
- When auditing your own plugin's prompts (self-audit), evaluate objectively as if reviewing external work.

---

## Severity Scale

| Severity | Meaning | Action |
|----------|---------|--------|
| **Critical** | Contradictions causing incorrect agent behavior, broken handoff contracts that break workflows, or hallucination-inducing gaps in safety-critical prompts | Fix immediately |
| **High** | Ambiguous directives with high divergence risk, missing completion signals, aggressive language causing overtrigger, scope conflicts between layers | Fix this sprint |
| **Medium** | Token bloat, redundancy, structural ordering issues, missing rationale, inconsistent formatting | Fix next sprint |
| **Low** | Style inconsistency, minor naming differences, optimization opportunities, excessive examples | Fix when convenient |

---

## Remediation Tiers

| Tier | Timeframe | Focus |
|------|-----------|-------|
| **Tier 1 -- Immediate** | This sprint | Contradictions (#6-10), broken contracts (#22), missing completion signals (#21), hallucination gaps (#30) |
| **Tier 2 -- Short Term** | Next 2 sprints | Specification gaps (#1-5), aggressive language (#26), structural reorganization (#11-15) |
| **Tier 3 -- Medium Term** | Next quarter | Token optimization (#16-20), cross-file deduplication (#17), skill extraction |
| **Tier 4 -- Ongoing** | Continuous | Naming standardization (#23), orphan cleanup (#25), documentation, prevention rules |

---

## Finding Report Format

Each agent outputs findings in this structure:

```markdown
## Findings

### [SEVERITY] Finding title

- **File**: path/to/agent.md
- **Section**: heading or line reference within the file
- **Defect**: #N -- Defect Name
- **Issue**: What is wrong
- **Evidence**: The specific excerpt from the prompt showing the problem
- **Impact**: Concrete behavioral harm (incorrect output, broken workflow, wasted tokens, inconsistency)
- **Fix**: How to fix it -- specific, actionable rewrite or guidance
- **Effort**: S (< 1 hour) / M (hours) / L (days)
```

### When No Defects Are Found

If your analysis finds no defects in your assigned categories, write:

```markdown
## Findings

No defects detected in categories #N-M. [One sentence explaining why the system is clean in this area, e.g., "All agents use consistent naming conventions matching the shared skill's terminology."]
```

## Strengths Section

Each agent must also note well-crafted aspects of the prompts:

```markdown
## Strengths

- **[aspect]**: Why this is effective and what makes it a good pattern to preserve
```

---

## Input Conventions

The orchestrator provides the output directory path in each agent's spawn prompt. All `{output-dir}` references in this skill and in agent files resolve to that path.

- **Phase 2 agents**: Read `{output-dir}/01-inventory.json` for the file list, handoff graph, and metrics. Read all source prompt files referenced in the inventory.
- **Phase 3 (synthesis)**: Read all prior outputs (`{output-dir}/01-inventory.json` through `{output-dir}/07-antipatterns.md`).
- **Phase 4 (remediation)**: Read synthesis (`{output-dir}/08-synthesis.md`) plus detail files (`{output-dir}/02-coherence.md` through `{output-dir}/07-antipatterns.md`) and source prompt files as needed.

---

## File-Saving Instructions

1. Write your complete output to your designated file under `{output-dir}/`.
2. Do not write to any other agent's file.
3. Signal completion with: `[prompt-audit-<name>] COMPLETE ✓ -- saved to {output-dir}/<filename>`

---

## Expected Output Sections by Agent

Each Phase 2 agent must include `## Findings` and `## Strengths` (from this skill), plus their agent-specific custom section:

| Agent | Custom Section |
|-------|---------------|
| prompt-audit-coherence | **Conflict Map** — table of file pairs with contradictions |
| prompt-audit-specification | **Specification Coverage** — matrix of agents vs. spec completeness |
| prompt-audit-structure | **Structural Summary** — table of files vs. ordering/formatting grades |
| prompt-audit-efficiency | **Token Budget** — table of files vs. waste estimates + **Duplication Clusters** |
| prompt-audit-consistency | **System Coherence** — dashboard of signal/contract/naming/tool checks |
| prompt-audit-antipatterns | **Anti-Pattern Heat Map** — table of files vs. defect counts + **Tone Calibration Summary** |

Phase 3 (synthesis) must include: Executive Summary, Key Metrics, File-Level Heat Map, Defect-Category Heat Map, Tiered Remediation Roadmap, Risk Assessment, Deduplicated Master Finding List.

Phase 4 (remediation) must include: Top 10 Before/After Rewrites, Consolidation Proposals, Structural Reorganization Plans, Prevention Rules.

---

## Prompt Defect Taxonomy

Reference material for all agents. Look up specific defect numbers as needed during analysis.

### A. Specification & Intent

| # | Defect | Detection Signal | Fix | Behavioral Risk |
|---|--------|-----------------|-----|-----------------|
| 1 | Ambiguous Directive | Vague verbs ("improve", "handle", "optimize", "process") without success criteria. Instructions that a reasonable person could interpret 2+ ways | Replace with specific, measurable instruction + concrete example of desired output | Agent interprets differently each run; outputs vary unpredictably across invocations |
| 2 | Underspecified Constraint | Missing output format, length bounds, or boundary requirements. No template or schema for expected output | Add explicit output spec with required sections, format template, or JSON schema | Agent invents output format; downstream consumer (orchestrator or next agent) fails to parse |
| 3 | Missing Success Criteria | No way to evaluate if the prompt achieved its goal. No completion conditions beyond "do the thing" | Add verifiable completion conditions: required sections, minimum coverage, validation checks | No quality gate; agent declares "done" at arbitrary quality level. Orchestrator cannot verify output |
| 4 | Intent Misalignment | Stated goal in description/header contradicts actual instruction body. Role definition says one thing, tasks say another | Align goal statement with instruction body. Ensure description, role, and tasks are coherent | Agent optimizes for wrong objective; output technically follows instructions but misses the point |
| 5 | Undefined Edge Cases | No guidance for empty inputs, error states, missing files, or boundary conditions. No fallback behavior specified | Add explicit handling: "If no files found, report empty inventory. If file is malformed, skip and note in warnings" | Agent hallucinates behavior for unspecified scenarios or silently produces wrong output |

### B. Coherence & Conflict

| # | Defect | Detection Signal | Fix | Behavioral Risk |
|---|--------|-----------------|-----|-----------------|
| 6 | Contradicting Instructions | Two directives that cannot both be followed. "Always include X" in one section, "Never include X" in another. Applies within a single file or across files in the same system | Remove contradiction. Pick one directive or add conditional ("Include X when Y, omit when Z") | Agent follows whichever instruction has more positional weight (usually the later one); behavior appears random |
| 7 | Priority Ambiguity | Multiple competing directives with no clear precedence. Two rules that partially overlap with different guidance for the overlap zone | Add explicit priority ordering: "Rule A takes precedence over Rule B when they conflict" or merge into single rule | Model resolves conflict using positional heuristics the author didn't intend; subtle behavioral drift |
| 8 | Example-Instruction Mismatch | Examples demonstrate behavior that contradicts stated rules. Instructions say "use JSON" but examples show markdown. Instructions say "be concise" but examples are verbose | Align examples with rules. If the example is correct, fix the rule. If the rule is correct, fix the example | Models often follow examples over instructions (especially with few-shot prompting); behavior follows the example |
| 9 | Scope Conflict | Skill file says "never X" but orchestrator spawn prompt says "always X". Agent-level rule contradicts system-level rule. Config injection overrides hardcoded instruction | Resolve at the authoritative source (usually the skill). Document which layer takes precedence | Silent override; agent behavior depends on context window ordering and model version |
| 10 | Cross-File Contradiction | Two agents in the same system given mutually exclusive behavioral rules for the same domain. Agent A told "format as JSON", Agent B told "format as markdown" for the same data | Centralize shared rules in skill file. Agents inherit via `skills:` frontmatter instead of duplicating | System produces inconsistent outputs across agents; downstream consumers must handle multiple formats |

### C. Structure & Formatting

| # | Defect | Detection Signal | Fix | Behavioral Risk |
|---|--------|-----------------|-----|-----------------|
| 11 | Poor Instruction Ordering | Critical behavioral instructions buried after lengthy context, examples, or reference material. Key constraints appear only at the end of a long prompt | Move critical instructions to the top (for attention) or reinforce at the end (for recency). Use both positions for highest-priority rules | Instructions at the bottom get higher weight (OpenAI recency bias); buried-middle instructions get lowest attention (lost-in-the-middle effect) |
| 12 | Missing Role Separation | System instructions, context data, user input templates, and examples mixed without clear boundaries. No XML tags, headers, or delimiters between sections | Use consistent delimiters: XML tags (`<instructions>`, `<context>`, `<examples>`) or markdown headers with clear hierarchy | Model confuses data for instructions. Context examples get treated as behavioral rules. User input templates get executed |
| 13 | Overloaded Prompt | Single prompt handling >3 distinct task categories or responsibilities. Agent is asked to analyze, decide, implement, and verify in one pass | Split into focused agents or explicit sequential steps within the prompt. Each step should have clear input/output | Context dilution; agent partially completes each task or focuses on the first/last while neglecting the middle |
| 14 | Inconsistent Formatting | Mixed XML tags, markdown headers, plain text bullets, and numbered lists without consistent purpose. Heading levels skip or repeat. Tag names vary (`<task>` vs `<instructions>` vs `<steps>`) | Standardize on one formatting system throughout. Use consistent tag/heading names. Establish hierarchy convention | Parser confusion; model misidentifies section boundaries. Nested content may be attributed to wrong section |
| 15 | Missing Output Format | No specification for expected output shape, required fields, or structure. Agent told "produce findings" without defining what a finding looks like | Add explicit output template with required sections and field definitions. Show one complete example | Agent invents format each run; orchestrator's validation logic breaks. Cross-agent synthesis fails on inconsistent formats |

### D. Efficiency & Token Economy

| # | Defect | Detection Signal | Fix | Behavioral Risk |
|---|--------|-----------------|-----|-----------------|
| 16 | Redundant Instructions | Same directive stated 2+ times in different words within a single file. "Always cite sources" appears as a rule, then repeated in examples section, then again in output format | Consolidate into single authoritative statement in the most prominent position | Wastes attention budget. May cause over-emphasis (model becomes fixated on the repeated instruction at the expense of others) |
| 17 | Cross-File Duplication | Identical or near-identical instruction blocks (>3 sentences) copy-pasted across multiple agent or skill files. Same boilerplate in every agent | Extract to shared skill file. Agents inherit via `skills:` frontmatter. Keep only agent-specific instructions in agent files | Maintenance nightmare: copies drift apart over time. Fix applied to one copy missed in others. Increases total token load across system |
| 18 | Token Bloat | Verbose explanations where concise phrasing achieves the same result. Excessive qualifiers, hedging language, or throat-clearing. Multiple sentences to express what one sentence could | Tighten prose. Replace paragraphs with bullet points where appropriate. Cut filler words (very, really, essentially, basically) | Every unnecessary token degrades recall accuracy (context rot). Longer prompts cost more and run slower |
| 19 | Excessive Examples | More than 5 examples for simple tasks, or examples that don't add coverage beyond the first 2-3. Redundant examples showing the same pattern with trivial variations | Reduce to 2-3 diverse examples covering the main case + key edge cases. Remove examples that don't add new information | Examples consume tokens that could carry instructions. Diminishing returns after 3-5 examples (Anthropic guidance) |
| 20 | Front-Loaded Context | All reference material, documentation, or background dumped into the prompt upfront instead of enabling runtime retrieval via tools | Provide file paths or tool instructions for just-in-time retrieval. Only include context the agent needs immediately | Agent's context fills before reaching instructions. Anthropic recommends "just-in-time" retrieval with lightweight pointers |

### E. Cross-Agent System

| # | Defect | Detection Signal | Fix | Behavioral Risk |
|---|--------|-----------------|-----|-----------------|
| 21 | Missing Completion Signal | Agent has no clear done/success indicator. No `[name] COMPLETE` pattern or equivalent. Orchestrator has no way to verify the agent finished | Add standard completion signal: `[agent-name] COMPLETE ✓ -- saved to {path}` as the final output line | Orchestrator cannot verify agent finished. Workflow may stall waiting for signal that never comes, or proceed on partial output |
| 22 | Broken Handoff Contract | Output format of agent A doesn't match the expected input format of agent B. Agent A writes markdown but agent B expects JSON. Agent A uses field name "findings" but agent B looks for "results" | Align output/input contracts. Define shared schema in skill file. Add validation step in orchestrator between agents | Downstream agent fails to parse upstream output. Chain breaks silently or produces garbage |
| 23 | Inconsistent Naming | Agents use different naming patterns for same concepts. One agent uses `finding-id`, another uses `findingId`, a third uses `finding_id`. Severity labels differ across agents | Standardize naming conventions in shared skill. Use consistent terminology throughout the system | Grep and search across system fails. Synthesis agent can't correlate findings. Cognitive overhead for maintainers |
| 24 | Tool Declaration Mismatch | Agent declares tools in frontmatter that it never uses, or agent's instructions require tools not declared. Agent has `Write` but instructions say "do not write files." Agent needs `WebSearch` but only has `Read` | Audit actual tool usage vs. declaration. Right-size tool sets: only declare tools the agent needs | Unnecessary tools create decision ambiguity (agent may use a tool it shouldn't). Missing tools cause silent failure (agent tries, fails, hallucinates result) |
| 25 | Orphaned Agent | Agent file exists in agents/ directory but is never referenced by any orchestrator command. No command spawns it. No documentation mentions it | Delete the orphaned agent, or integrate it into an orchestrator command | Dead code; confuses maintainers who wonder what it does. May be loaded by plugin index, wasting resources |

### F. Anti-Pattern & Tone

| # | Defect | Detection Signal | Fix | Behavioral Risk |
|---|--------|-----------------|-----|-----------------|
| 26 | Aggressive Language Overtrigger | Excessive use of "CRITICAL", "MUST", "NEVER", "ABSOLUTELY", "IMPORTANT" (>3 emphatic markers per file). ALL CAPS for non-critical instructions | Reserve emphatic language for genuinely critical constraints (security, data safety). Use calm, direct tone for everything else | Claude 4.6 is documented to overtrigger on aggressive language. Model becomes overly cautious, fixated on emphasized rules at the expense of overall task completion |
| 27 | Negative Framing | Instructions phrased as prohibitions without providing the desired alternative. "Don't use markdown" without saying what to use. "Never guess" without saying what to do instead | Replace "don't do X" with "do Y instead of X." Provide the positive behavior, not just the prohibition | Model knows what to avoid but not what to do. May freeze, hallucinate an alternative, or do nothing |
| 28 | Missing Rationale | Non-obvious instructions given without explaining why. Rules that seem arbitrary without context. Constraints that a reader would question without background | Add brief rationale for non-obvious rules. Format: "Do X because Y" or "Do X -- this prevents Y" | Model follows the letter but not the spirit. Fails to generalize to novel situations where the same principle applies |
| 29 | Brittleness Pattern | Over-specified conditional logic enumerating every possible scenario instead of providing higher-level guidance. Long if/then/else chains in natural language | Raise abstraction level. State the principle, not every instance. Let the model reason about edge cases using the principle | Breaks on any scenario not explicitly enumerated. High maintenance: every new scenario requires a prompt edit |
| 30 | Hallucination-Inducing Gap | References to undefined acronyms, external documents not provided, tools not available, or knowledge assumed but not stated. Prompt says "follow the playbook" without providing the playbook | Provide the missing context inline, via file path, or via tool instruction. Define all acronyms on first use | Model fabricates content with high confidence. Hallucinated tool usage, invented file paths, or made-up references |
