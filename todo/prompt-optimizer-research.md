# Prompt Optimization Agent — Research Synthesis

## Purpose

Research findings to inform the design of a **prompt tightening and optimization agent** that analyzes prompts, skills, and agent systems to identify discrepancies, incoherence, opposing instructions, and propose improvements.

---

## 1. Foundational Frameworks from Major LLM Providers

### 1.1 Anthropic — Context Engineering (2025)

**Source**: [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

Anthropic frames the evolution from "prompt engineering" to **context engineering** — curating and managing the *entire token configuration* during inference, not just the prompt text.

**Key principles:**

| Principle | Description |
|-----------|-------------|
| **Right Altitude** | System prompts must sit between two failure modes: *brittleness* (over-specified conditional logic) and *vagueness* (abstract guidance lacking behavioral signals). |
| **Minimalism** | Find the *smallest set of high-signal tokens* maximizing desired outcome. Minimal ≠ short — agents still need sufficient upfront information. |
| **Progressive Disclosure** | Allow agents to incrementally discover context through exploration rather than front-loading everything. |
| **Just-In-Time Retrieval** | Maintain lightweight pointers (file paths, queries, URLs) and dynamically load data using tools at runtime. |
| **Context Rot** | As tokens increase, accuracy of recall decreases — not a cliff but a gradient. Every token depletes the model's finite "attention budget." |

**Anti-patterns identified:**
- Hardcoding complex conditional logic (creates fragility, escalates maintenance)
- Bloated tool sets with overlapping functionality (creates decision ambiguity)
- Stuffing prompts with situational rules instead of canonical examples
- Front-loading all context instead of enabling runtime retrieval

### 1.2 Anthropic — Claude 4 Best Practices (2025-2026)

**Source**: [Prompting Best Practices — Claude 4](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)

**Structural recommendations:**
- Use XML tags (`<instructions>`, `<context>`, `<input>`) to delineate prompt sections unambiguously
- Put longform data at the top, queries/instructions at the bottom (up to 30% quality improvement)
- Use numbered lists or bullet points when step order or completeness matters
- Provide 3-5 diverse examples wrapped in `<example>` tags
- Tell Claude what to do *instead of* what not to do

**Key behavioral insights for Claude 4.6:**
- More responsive to system prompts — aggressive language ("CRITICAL: You MUST") can cause overtriggering
- Less verbose by default — may skip summaries after tool calls
- Strong tendency toward subagent orchestration — may over-spawn when direct approach suffices
- May overengineer (extra files, unnecessary abstractions)

**Golden rule**: "Show your prompt to a colleague with minimal context and ask them to follow it. If they'd be confused, Claude will be too."

### 1.3 OpenAI — GPT-4.1 Prompting Guide (2025)

**Source**: [GPT-4.1 Prompting Guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide)

**Three essential agentic system prompt components** (increased SWE-bench scores by ~20%):

1. **Persistence**: "Keep going until the user's query is completely resolved"
2. **Tool-Calling**: "Use your tools to read files and gather information; do NOT guess or make up answers"
3. **Planning** (optional): "Plan extensively before each function call, and reflect on previous outcomes"

**Instruction priority rule**: The model prioritizes instructions appearing **later** in the prompt. When conflicting directives exist, the latter wins.

**Anti-patterns:**
- Mandating tool calls without conditioning (prevents appropriate fallback to asking user)
- Overusing sample phrases without variation instructions (repetitive outputs)
- Relying on ALL CAPS, "bribes," or excessive formatting — start simple and escalate only if needed
- Examples that contradict stated rules

**Tool design:**
- Use native API `tools` field, not manual schema injection (+2% performance)
- Clear descriptive naming, detailed parameter descriptions
- Place usage examples in a dedicated prompt section, not inside tool descriptions

### 1.4 OpenAI — Reasoning Models Best Practices

**Source**: [Reasoning Best Practices](https://platform.openai.com/docs/guides/reasoning-best-practices)

- Keep prompts simple and direct for reasoning models
- Don't say "think step by step" — the model reasons internally
- Audit failures in examples/evals and address *systematic* planning errors with explicit instructions
- Common error categories: misunderstanding intent, insufficient context gathering, incorrect step-by-step thinking

### 1.5 Google Cloud — Vertex AI Prompt Optimizer

**Source**: [Vertex AI Prompt Optimizer](https://cloud.google.com/blog/products/ai-machine-learning/announcing-vertex-ai-prompt-optimizer)

Google's production-grade APO system:
- Iterative LLM-based optimization: optimizer generates paraphrased instructions, evaluator assesses them
- Finds best prompt instructions AND demonstrations for any model
- Available as a managed service on Vertex AI

---

## 2. Academic Research on Automatic Prompt Optimization

### 2.1 Taxonomy of APO Methods

**Source**: [A Systematic Survey of Automatic Prompt Optimization Techniques](https://arxiv.org/html/2502.16923v1) (EMNLP 2025)

The survey presents a **5-part unifying framework** for APO:

```
Seed Initialization → Inference & Evaluation → Candidate Generation → Filter & Retain → Iterate
```

**Generation techniques classified:**

| Category | Methods | Key Idea |
|----------|---------|----------|
| Heuristic Edits | Monte Carlo, genetic algorithms, vocabulary pruning | Random/evolutionary search over prompt space |
| Metaprompt Design | OPRO, APE | Include prior solutions + scores to guide refinement |
| Coverage-Based | Ensemble, mixture-of-experts | Ensure semantic facets are represented |
| Program Synthesis | DSPy, MIPRO | Treat prompts as compilable programs |
| Neural Networks | RL, finetuning, GANs | Learned prompt generators |

**Feedback mechanisms:**
- Numeric scoring (accuracy, reward models, entropy)
- LLM-based feedback ("textual gradients" for discrete optimization)
- Human preference signals

**Open challenges (directly relevant to our agent):**
- Task specificity — most methods assume known task types
- Interpretability — why optimized prompts work remains unclear
- **System-level optimization** — scaling to multi-component agent systems is underexplored
- Multimodal prompt optimization is nascent

### 2.2 OPRO — Large Language Models as Optimizers (Google DeepMind)

**Source**: [Large Language Models as Optimizers](https://arxiv.org/abs/2309.03409) — Yang et al., 2023 (ICLR 2024)

**Core idea**: Describe optimization in natural language. In each step:
1. LLM generates new candidate solutions from a meta-prompt containing prior solutions + scores
2. New solutions are evaluated and added to the meta-prompt
3. Repeat

**Results**: Best prompts outperform human-designed prompts by up to 8% (GSM8K) and 50% (Big-Bench Hard).

**Limitation**: [Revisiting OPRO](https://arxiv.org/abs/2405.10276) shows limited effectiveness with smaller-scale LLMs.

### 2.3 DSPy — Programming (Not Prompting) LMs (Stanford NLP)

**Source**: [DSPy: Compiling Declarative Language Model Calls](https://arxiv.org/abs/2310.03714) — Khattab et al., 2023

**Paradigm shift**: Replace brittle prompt strings with compositional Python code. DSPy *compiles* declarative modules into optimized prompts.

**Key optimizers:**
- **BootstrapFewShot**: Teacher model generates demonstrations, metric validates them
- **MIPRO**: Samples mini-batches, proposes instruction+trace combinations, uses surrogate model to improve proposals
- **GEPA**: Reflects on program trajectories to identify what worked/didn't, proposes prompt fixes

**Performance**: GPT-3.5 with DSPy-compiled prompts outperforms expert-crafted prompts by 5-46%.

**Relevance to our agent**: DSPy's compilation model proves that *structured, metric-driven prompt optimization* works at scale. Our agent can borrow the reflect-and-refine loop.

### 2.4 MIPRO — Multi-Stage LM Program Optimization

**Source**: [Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs](https://arxiv.org/abs/2406.11695)

Specifically targets **multi-stage pipelines** (relevant to our multi-agent system):
- Outperforms baselines on 5/7 diverse multi-stage programs by up to 13%
- Jointly optimizes instructions AND demonstrations across stages
- Uses Bayesian optimization with a surrogate model

### 2.5 UniPrompt & CRISPO — Semantic Facet Coverage

**UniPrompt**: Ensures various semantic facets of a task are represented in the final prompt via two stages: facets initialization and refinement.

**CRISPO** (Multi-Aspect Critique-Suggestion-Guided APO): Generates critiques across multiple aspects, then uses them to guide prompt refinement. Directly relevant to our "identify discrepancies" use case.

---

## 3. Prompt Defect Taxonomy (The Academic Foundation for Our Agent)

### 3.1 A Taxonomy of Prompt Defects in LLM Systems

**Source**: [A Taxonomy of Prompt Defects in LLM Systems](https://arxiv.org/abs/2509.14404) — Tian et al., 2025

This is the **most directly applicable** paper. It presents the first systematic taxonomy of prompt defects, organized in 6 dimensions with granular subtypes. This taxonomy can serve as the **checklist/ruleset** for our optimization agent.

#### Dimension 1: Specification & Intent Defects
| Defect | Description | Detection Strategy |
|--------|-------------|-------------------|
| **Ambiguous Instructions** | Multi-interpretable directives ("make it better") | Flag vague verbs, missing success criteria |
| **Underspecified Constraints** | Missing format, coverage, or boundary requirements | Check for undefined outputs, missing edge case handling |
| **Conflicting Instructions** | Internally inconsistent directives | Pairwise comparison of instruction clauses |
| **Intent Misalignment** | Prompt doesn't reflect true goals | Compare stated goal vs. actual instruction content |

#### Dimension 2: Input & Content Defects
| Defect | Description | Detection Strategy |
|--------|-------------|-------------------|
| **Misleading Information** | Wrong facts or false premises | Cross-reference against known facts/context |
| **Malicious Injection** | Hidden override instructions | Scan for instruction-like patterns in data sections |
| **Cross-Modal Misalignment** | Conflicting text vs. examples | Compare demonstrated behavior to stated rules |

#### Dimension 3: Structure & Formatting Defects
| Defect | Description | Detection Strategy |
|--------|-------------|-------------------|
| **Lack of Role Separation** | System/user/assistant boundaries unclear | Check for proper message role usage |
| **Poor Organization** | Context, rules, questions in wrong order | Validate ordering against best practices |
| **Overloaded Prompt** | Too many simultaneous tasks | Count distinct task directives |
| **Undefined Output Format** | No specification for answer shape | Check for format specifications |

#### Dimension 4: Context & Memory Defects
| Defect | Description | Detection Strategy |
|--------|-------------|-------------------|
| **Irrelevant/Noisy Context** | Unnecessary information dilutes critical instructions | Measure signal-to-noise ratio |
| **Forgotten Instructions** | Key directives fade due to distance from active context | Check if critical rules are reinforced/pinned |
| **Conversational Misreferencing** | Ambiguous references ("that code", "the function") | Flag vague referents |

#### Dimension 5: Performance & Efficiency Defects
| Defect | Description | Detection Strategy |
|--------|-------------|-------------------|
| **Excessive Length** | Overly long prompts with redundant content | Measure token count, identify redundancies |
| **Inefficient Examples** | Too many or overly complex demonstrations | Count examples vs. minimum effective |
| **Unbounded Output** | No length or detail constraints | Check for output constraints |

#### Dimension 6: Maintainability & Engineering Defects
| Defect | Description | Detection Strategy |
|--------|-------------|-------------------|
| **Hard-Coded Prompts** | Duplicated across locations | Detect copy-paste patterns across agent/skill files |
| **Poor Documentation** | Purpose and intricacies undocumented | Check for missing intent/rationale comments |
| **Integration Mismatch** | Output doesn't match expected contract | Validate output specs against downstream consumers |

---

## 4. Cross-Source Synthesis: Principles for the Optimization Agent

### 4.1 Converging Principles Across All Sources

These principles appear consistently across Anthropic, OpenAI, Google, and academic research:

1. **Clarity over cleverness** — Every source emphasizes explicit, unambiguous instructions. Vague prompts are the #1 failure mode.

2. **Structure matters** — XML tags (Anthropic), markdown headers, or explicit sections prevent misinterpretation. Ordering affects priority (OpenAI: later instructions win).

3. **Minimal effective prompts** — Include only what's needed. Extra tokens degrade attention. But minimal ≠ short — agents need sufficient context.

4. **Examples > exhaustive rules** — Well-chosen examples convey understanding more efficiently than enumerating every edge case.

5. **Test and iterate** — All sources frame prompt engineering as empirical science requiring evals and iteration. No one-size-fits-all.

6. **Separate concerns** — System instructions, user input, examples, and context should be clearly delineated.

7. **Context about context** — Explaining *why* an instruction exists helps the model generalize correctly (Anthropic: "Claude is smart enough to generalize from the explanation").

### 4.2 Defect Categories Our Agent Should Detect

Based on the taxonomy and provider guidelines, the agent should check for:

#### A. Coherence Checks
- **Contradicting instructions**: Two directives that cannot both be followed
- **Scope conflicts**: Agent told to "never X" in one place and "always X" in another
- **Priority ambiguity**: Multiple competing directives with no clear precedence
- **Example-instruction mismatch**: Examples that demonstrate behavior contradicting stated rules

#### B. Structural Checks
- **Missing role separation**: System/user/assistant boundaries unclear
- **Poor ordering**: Critical instructions buried deep (should be at top or reinforced)
- **Overloaded prompts**: Single prompt trying to handle too many distinct tasks
- **Missing output format**: No specification for expected output shape
- **Inconsistent formatting**: Mixed use of XML, markdown, plain text without clear purpose

#### C. Specification Checks
- **Vague directives**: Verbs like "improve," "optimize," "handle" without criteria
- **Missing success criteria**: No way to evaluate if the prompt achieved its goal
- **Undefined edge cases**: Missing guidance for boundary conditions
- **Implicit assumptions**: Knowledge assumed but not stated

#### D. Efficiency Checks
- **Redundant instructions**: Same thing said multiple ways
- **Excessive examples**: More examples than needed to establish the pattern
- **Token bloat**: Verbose explanations where concise ones suffice
- **Duplicated content**: Same instructions copy-pasted across multiple agents/skills

#### E. Cross-Agent Consistency Checks
- **Conflicting conventions**: Different agents using different naming, formatting, or behavioral conventions
- **Missing completion signals**: Agents without clear done/success indicators
- **Inconsistent tool usage**: Agents with overlapping tool sets creating ambiguity
- **Broken handoff contracts**: Output of one agent doesn't match expected input of the next

#### F. Anti-Pattern Detection
- **Brittleness patterns**: Over-specified conditional logic that should be higher-level guidance
- **Aggressive language**: "CRITICAL", "MUST", "NEVER" overuse (especially on Claude 4.6 which overtriggers)
- **Negative framing**: "Don't do X" instead of "Do Y instead"
- **Missing rationale**: Instructions without explaining *why* (reduces model's ability to generalize)
- **Hallucination-inducing gaps**: Missing context that forces the model to guess

### 4.3 Optimization Strategies the Agent Should Propose

Based on OPRO, DSPy, and CRISPO patterns:

1. **Reflect-and-Refine Loop**: Analyze prompt → identify defects → generate improved version → compare
2. **Semantic Facet Coverage**: Ensure all necessary aspects of the task are addressed (UniPrompt approach)
3. **Multi-Aspect Critique**: Generate critiques from multiple perspectives (CRISPO: clarity, completeness, coherence, efficiency)
4. **Instruction Consolidation**: Merge scattered related instructions into cohesive blocks
5. **Priority Ordering**: Restructure to put high-priority instructions where the model weights them most
6. **Example Curation**: Suggest adding/removing/modifying examples based on coverage gaps
7. **Cross-Reference Validation**: Compare instructions across related agents/skills for consistency

---

## 5. Proposed Agent Architecture

Based on research findings, the prompt optimization agent should operate in phases:

### Phase 1: Inventory & Parse
- Read all prompt/skill/agent files in scope
- Parse into structured components (system instructions, examples, tool definitions, output specs)
- Build a dependency/handoff graph between agents

### Phase 2: Individual Prompt Analysis
- Run each prompt through the 6-dimension defect taxonomy
- Score severity (critical/warning/info) for each finding
- Map findings to specific line ranges

### Phase 3: Cross-System Analysis
- Check inter-agent consistency (naming, conventions, contracts)
- Validate handoff chains (output format of agent A matches expected input of agent B)
- Detect duplicated or contradicting instructions across the system

### Phase 4: Optimization Proposals
- Generate concrete rewrites for each finding
- Prioritize by impact (coherence > structure > efficiency)
- Group related changes to avoid conflicting fixes

### Phase 5: Validation
- Verify proposed changes don't introduce new conflicts
- Check that changes preserve original intent
- Generate before/after diff for human review

---

## 6. Key Sources

### Primary (from major LLM creators)
- [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic, 2025
- [Prompting Best Practices — Claude 4](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices) — Anthropic, 2025-2026
- [Claude Code: Best Practices for Agentic Coding](https://www.anthropic.com/engineering/claude-code-best-practices) — Anthropic, 2025
- [Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents) — Anthropic, 2025
- [GPT-4.1 Prompting Guide](https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide) — OpenAI, 2025
- [GPT-5 Prompting Guide](https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide) — OpenAI, 2025
- [Reasoning Best Practices](https://platform.openai.com/docs/guides/reasoning-best-practices) — OpenAI, 2025
- [Vertex AI Prompt Optimizer](https://cloud.google.com/blog/products/ai-machine-learning/announcing-vertex-ai-prompt-optimizer) — Google Cloud, 2024

### Academic Papers
- [A Taxonomy of Prompt Defects in LLM Systems](https://arxiv.org/abs/2509.14404) — Tian et al., 2025 (foundational defect classification)
- [Large Language Models as Optimizers (OPRO)](https://arxiv.org/abs/2309.03409) — Yang et al., Google DeepMind, 2023/ICLR 2024
- [DSPy: Compiling Declarative Language Model Calls](https://arxiv.org/abs/2310.03714) — Khattab et al., Stanford NLP, 2023
- [A Systematic Survey of Automatic Prompt Optimization](https://arxiv.org/abs/2502.16923) — EMNLP 2025 (comprehensive APO taxonomy)
- [A Survey of APE: An Optimization Perspective](https://arxiv.org/abs/2502.11560) — 2025 (APE/CRISPO/MOP/DSPy/OPRO/GATE comparison)
- [Optimizing Instructions for Multi-Stage LM Programs (MIPRO)](https://arxiv.org/abs/2406.11695) — 2024
- [Revisiting OPRO: Limitations of Small-Scale LLMs](https://arxiv.org/abs/2405.10276) — 2024
- [Prompt Engineering and LLM Effectiveness](https://arxiv.org/html/2507.18638v2) — 2025
- [Promptolution: Unified Framework for Prompt Optimization](https://arxiv.org/html/2512.02840v1) — 2025
- [Error Taxonomy-Guided Prompt Optimization](https://arxiv.org/html/2602.00997) — 2026

### Additional Reputable Sources
- [Equipping Agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — Anthropic, 2025
- [Writing Tools for Agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — Anthropic, 2025
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Anthropic, 2025
- [Prompt Engineering for Long Context](https://www.anthropic.com/news/prompting-long-context) — Anthropic
- [Prompt Engineering for Business Performance](https://www.anthropic.com/news/prompt-engineering-for-business-performance) — Anthropic
- [Is It Time to Treat Prompts as Code?](https://arxiv.org/html/2507.03620v1) — DSPy multi-use case study, 2025
