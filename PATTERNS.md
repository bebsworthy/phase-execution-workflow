# Orchestrator Patterns for Claude Code Plugins

Hard-won lessons from building PEW's multi-agent workflow, cross-referenced against official Anthropic documentation and community patterns. Last updated: March 2026.

---

## The Core Problem

When a skill prompt tells the main agent to "read the codebase, analyze it, then write a document," the agent loads everything into its own context window. By step 3 of a 7-step workflow, the context is bloated with source code, research docs, and prior artifacts — making the agent slow, expensive, and prone to losing track of instructions.

Anthropic's own research confirms this: in their multi-agent research system, **80% of quality variance is explained by token usage**. Multi-agent is primarily a mechanism to spend tokens efficiently across isolated contexts rather than cramming everything into one.

## The Fix: Thin Orchestrator + File-Based Communication

The orchestrator never reads source code or writes documents. It dispatches agents, validates their output files, and manages lifecycle (gates, commits, status). Agents communicate through files, not through the orchestrator's context.

```
Orchestrator context contains:  config, phase metadata, file paths, gate results
Orchestrator context does NOT contain:  source code, artifact content, research findings
```

---

## Hard Constraints (Verified Against Official Docs — March 2026, Claude Code v2.1.76)

### 1. Sub-agents cannot spawn sub-agents

Depth limit is exactly 1. Only the main conversation (or `claude --agent` top-level) can use the Agent tool.

> "Subagents cannot spawn other subagents. Don't include `Agent` in a subagent's `tools` array."
> — Claude Agent SDK docs

> "Subagents cannot spawn other subagents. If your workflow requires nested delegation, use Skills or chain subagents from the main conversation."
> — Claude Code docs

**Implication**: All agent spawning must happen from the orchestrator. Design flat: one orchestrator, many leaf agents. If Step A's agent needs Agent B's output, the orchestrator chains them sequentially.

**Bug history**: In v2.1.48 (Feb 2026), a fix was shipped to prevent teammates from accidentally spawning nested teammates — confirming the constraint is enforced at the platform level, not just documented.

### 2. Context windows are isolated

Each spawned agent gets a fresh context window with no parent conversation history. The only channel from parent to subagent is the Agent tool's prompt string.

> "A subagent's context window starts fresh (no parent conversation) but isn't empty."
> — Claude Code docs

**What a subagent receives**: its own system prompt, the Agent tool's invocation prompt, project CLAUDE.md, specified MCP servers, tool definitions.

**What it does NOT receive**: parent conversation history, parent's system prompt, other subagent contexts, skills (unless explicitly listed in frontmatter).

**This is an advantage**: an agent analyzing 5,000 lines of code doesn't bloat the orchestrator. Only the agent's final message returns to the parent.

### 3. Only the final message returns

Intermediate tool calls and their results stay inside the subagent's context. The parent only sees the subagent's final text response. This means:

- Subagents are natural **context firewalls** — they compress large inputs into small summaries
- The orchestrator can't see what the agent read or how it reasoned
- Agents must write important outputs to files (not just return them) because the return message has limited space

### 4. No inter-subagent communication

> "Subagents only report results back to the main agent and never talk to each other."
> — Claude Code docs

For agents that need to coordinate, use file-based communication (shared filesystem) or have the orchestrator relay information.

---

## Dispatch Patterns

### Pattern 1: Sequential File Chain

Agents run one after another. Each reads the previous agent's output file.

```
Orchestrator:
  1. Spawn Agent A → writes file-a.md
  2. Validate file-a.md exists
  3. Spawn Agent B (input: path to file-a.md) → writes file-b.md
  4. Validate file-b.md exists
  5. Spawn Agent C (input: path to file-b.md) → writes file-c.md
```

**Key rule**: Pass file *paths*, not file *content*. Agents have Read/Glob/Grep tools — they read files themselves. This keeps the orchestrator's context clean.

**Real example** (PEW build workflow):
```
Orchestrator:
  1. Spawn build-ideas-writer → IDEAS.md
  2. Spawn build-brd-writer (input: IDEAS.md path) → BRD.md
  3. Spawn build-spec-writer (input: BRD.md path, RESEARCH.md path) → SPEC.md
```

**Real example** (PEW UX audit — the original inspiration):
```
Orchestrator:
  1. Spawn ux-audit-goals → 01-user-goals.md
  2. Spawn ux-audit-impl (input: 01-user-goals.md path) → 02-implementation.md
  3. Spawn ux-audit-research (input: 02-implementation.md path) → 03-patterns.md
  4. Spawn ux-audit-eval (input: 01-03.md paths) → 04-audit.md
  5. Spawn ux-audit-proposals (input: 01-04.md paths) → 05-proposals.md
```

### Pattern 2: Fan-Out / Fan-In

Multiple agents run in parallel on different slices of work. Orchestrator collects and merges results.

```
Orchestrator:
  1. Spawn Agent A, Agent B, Agent C  (in parallel, single message with multiple Agent calls)
  2. Collect structured output (JSON) from each
  3. Merge/deduplicate results (lightweight — no code reading)
  4. Write merged output to file
```

**Key rule**: Merging must be lightweight coordination (comparing JSON keys, deduplicating by ID), not deep analysis. If merging requires reading code, it belongs in an agent.

**Parallel safety note** (from v2.1.48 changelog): Sibling file mutations are now isolated — one file write error no longer aborts all parallel writes. Only Bash errors cascade. This makes parallel fan-out safer.

**Real example** (council review):
```
Orchestrator:
  1. Spawn council-security, council-architecture, council-testing (parallel)
  2. Collect JSON findings from each
  3. Deduplicate by (file, line_range)
  4. Write merged COUNCIL-REVIEW.md
```

### Pattern 3: Research-Then-Synthesize

When a step needs both external research and codebase analysis, split into separate agents run sequentially.

```
Orchestrator:
  1. Spawn Research Agent → writes research-output.md
  2. Spawn Synthesis Agent (input: research-output.md path + other inputs) → writes artifact.md
```

**Why not one agent?** Research agents need WebSearch/WebFetch tools. Synthesis agents need deep codebase access (Read/Grep/Glob). Combining both in one agent bloats its tool list and muddies its purpose. Separate agents = clearer contracts, smaller context per agent.

**Real example** (IDEAS step):
```
Orchestrator:
  1. Spawn build-feature-benchmarker → benchmark-<topic>.md  (uses WebSearch)
  2. Spawn build-ideas-writer (input: benchmark path) → IDEAS.md  (reads codebase)
```

### Pattern 4: Task Loop

The orchestrator iterates a structured task list, spawning one agent per task.

```
Orchestrator:
  1. Read task list from PLAN.md (lightweight — just IDs, descriptions, agent assignments)
  2. FOR each task in dependency order:
     a. Spawn assigned agent (input: task description, acceptance criteria, file paths)
     b. Wait for completion
     c. Update task status in PLAN.md
```

**Key rule**: The orchestrator reads only the task metadata (ID, description, agent type, dependencies). It does NOT read playbooks, review profiles, or source code — agents read those themselves given directory paths.

---

## Agent Design Rules

### Self-contained prompts

The only channel from parent to subagent is the Agent tool's prompt string. Include everything the agent needs:

```
# BAD — agent doesn't know what it's working on
"Write the BRD."

# GOOD — agent has all paths and context
"You are writing BRD.md for Phase 3 (Search Filtering).
Read IDEAS.md at phases/phase-3-search-filtering/IDEAS.md.
Read refs: ux-review/04-audit.md, ux-review/01-user-goals.md.
Read conventions at CONVENTIONS.md.
Write output to phases/phase-3-search-filtering/BRD.md.
Use template at ${CLAUDE_PLUGIN_ROOT}/templates/BRD.template.md for format reference."
```

### Focused tool sets

Don't give every agent every tool. Match tools to purpose:

| Agent type | Tools | Rationale |
| --- | --- | --- |
| Read-only reviewer | Read, Grep, Glob, Bash | Can analyze but not modify |
| Document writer | Read, Grep, Glob, Write, Edit | Reads context, writes artifact |
| Researcher | Read, Grep, Glob, Write, WebSearch, WebFetch | Needs external web access |
| Developer | Read, Grep, Glob, Bash, Write, Edit | Full implementation access |

### Completion signals

Agents should signal completion clearly:

```
[build-brd-writer] COMPLETE ✓ — saved to phases/phase-1/BRD.md
```

If an agent has unresolved questions:

```
[build-ideas-writer] COMPLETE WITH QUESTIONS — saved to phases/phase-1/IDEAS.md
OPEN QUESTIONS:
1. Should we support offline mode? (options: yes/no/defer)
2. Target mobile or desktop first?
```

The orchestrator picks up questions and presents them to the user via `AskUserQuestion`.

### No commits from agents

Keep commit authority centralized in the orchestrator. Agents write files; the orchestrator validates output and commits. This makes rollback straightforward — one actor controls the git timeline.

---

## Worktree Isolation

Since v2.1.49 (Feb 2026), agents can use git worktree isolation:

```yaml
---
name: api-worker
isolation: worktree
---
```

Each agent gets its own working directory with independent file state. Use when:
- Multiple agents edit the same files in parallel
- You want to prevent file conflicts between concurrent agents
- Changes need review before merging back

Worktrees are auto-cleaned if the agent makes no changes. Supports `worktree.sparsePaths` for monorepos (v2.1.72).

---

## Validation Pattern

After every agent completes, the orchestrator validates before proceeding:

1. **File exists**: The expected output file was created
2. **Non-empty**: The file has content (not just headers)
3. **Quality gate** (if applicable): Run traceability checks or similar
4. **Open questions**: If the agent flagged unresolved questions, present them to the user, then re-spawn the agent with answers

```
Orchestrator:
  spawn build-brd-writer → BRD.md
  assert BRD.md exists and is non-empty
  run verify-traceability --from ideas --to brd
  if traceability fails: handle resolution (fix/descope/defer)
  commit
  set-step-status complete
```

This gives the orchestrator just enough control to enforce quality without loading artifact content into its context.

---

## Anti-Patterns

### The God Orchestrator

```
# BAD: orchestrator reads everything, becomes the bottleneck
Orchestrator reads BRD.md (2000 tokens)
Orchestrator reads RESEARCH.md (1500 tokens)
Orchestrator reads codebase (5000 tokens)
Orchestrator writes SPEC.md
```

The orchestrator's context fills up. By BUILD step, it's sluggish and forgetful.

```
# GOOD: orchestrator dispatches, agents read and write
Orchestrator spawns build-spec-writer (input: BRD.md path, RESEARCH.md path)
Agent reads files in its own context, writes SPEC.md
Orchestrator validates SPEC.md exists
```

### Inline Content Passing

```
# BAD: orchestrator reads file content and passes it in the prompt
content = read("BRD.md")
spawn agent with prompt: f"Here is the BRD:\n{content}\nWrite a SPEC."

# GOOD: pass the path, let the agent read it
spawn agent with prompt: "Read BRD.md at phases/phase-1/BRD.md. Write SPEC.md."
```

Passing content inline wastes the orchestrator's context tokens and duplicates information (it exists in the file AND in the prompt). This is a known limitation — GitHub issue #4908 requests scoped context passing as a first-class feature.

### Premature Merging

```
# BAD: orchestrator reads all research to "understand" before spawning spec writer
Orchestrator reads benchmark.md
Orchestrator reads ux-research.md
Orchestrator reads architecture-reference.md
Orchestrator "summarizes" for spec writer

# GOOD: pass all paths, let the agent decide what it needs
Orchestrator spawns build-spec-writer(
  brd_path, research_path, design_path, arch_ref_path
)
```

The agent is better positioned to decide what it needs from each file.

### Permission Prompt Flooding

When running multiple parallel agents, each agent may trigger permission prompts independently. Pre-configure permissions in `.claude/settings.json` for common operations (file reads, linting commands, test runs) before spawning agents. Without this, parallel workflows grind to a halt waiting for user approvals.

---

## Agent Teams (Experimental Alternative)

Since v2.1.32 (Feb 2026), Claude Code supports **Agent Teams** — multiple independent Claude instances with direct inter-agent communication. This is a fundamentally different model from subagents.

| Aspect | Subagents | Agent Teams |
| --- | --- | --- |
| Communication | Via parent only | Direct inter-agent messaging |
| Context | Fresh per-agent, parent sees final message | Fully independent per-agent |
| Coordination | Orchestrator-driven | Self-coordinating via shared task list |
| Token cost | Moderate | Significantly higher |
| Status | Stable | Experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) |
| Nesting | Cannot spawn subagents | Cannot spawn sub-teams |

Agent Teams are better for sustained parallel work where agents need to coordinate (like Anthropic's 16-agent C compiler build). Subagents are better for discrete, well-scoped tasks dispatched by an orchestrator.

**Lock-file pattern from Anthropic's C compiler project**: Agents claim tasks by writing lock files. Simple but prevents duplicate work across parallel agents.

---

## The Hierarchy of What Actually Works

From most to least battle-tested:

1. **Single agent with subagent delegation** — official, well-documented, production-proven
2. **Orchestrator-worker with context isolation** — Anthropic's own research system uses this pattern
3. **Agent Teams for parallel exploration** — official but experimental
4. **External orchestrator** — community workaround for nesting constraint (Python script chaining `claude` CLI invocations)

Anthropic's own advice: *"Start with simple prompts, optimize with comprehensive evaluation, and add multi-step agentic systems only when simpler solutions fall short."*

---

## Lifecycle Hooks

Available hooks for agent lifecycle management:

| Hook Event | When | Use Case |
| --- | --- | --- |
| `SubagentStart` | Agent begins execution | Setup resources, inject config |
| `SubagentStop` | Agent completes | Cleanup, aggregate results |
| `PreToolUse` | Before tool executes (in agent) | Validate operations |
| `PostToolUse` | After tool succeeds (in agent) | Audit, lint |
| `WorktreeCreate` | Worktree created for agent | Setup worktree-specific resources |
| `WorktreeRemove` | Worktree cleaned up | Cleanup worktree resources |

PEW uses a `SubagentStart` hook (defined in `plugin.json`) to auto-inject resolved `pew.yaml` config into every PEW agent. The hook maps agent type to a config scope (`agent`, `council`, `research`), runs `pw.sh dump-config --scope <scope>`, and outputs the result as `additionalContext`. Non-PEW agents (Explore, Plan, general-purpose) are ignored.

---

## Key References

**Official (highest reliability)**:
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) — Anthropic's canonical patterns guide
- [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system) — Production case study, orchestrator-worker pattern
- [Building a C Compiler with 16 Parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) — Agent Teams at scale
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Context management strategies
- [Claude Code Subagent Docs](https://code.claude.com/docs/en/sub-agents) — Official subagent reference
- [Claude Code Agent Teams Docs](https://code.claude.com/docs/en/agent-teams) — Team orchestration reference
- [Claude Agent SDK Demos](https://github.com/anthropics/claude-agent-sdk-demos) — Official SDK examples

**Community (cross-referenced against official docs)**:
- [Swarm Orchestration Gist](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea) — Hidden TeammateTool patterns (extracted from binary, may change)
- [barkain/claude-code-workflow-orchestration](https://github.com/barkain/claude-code-workflow-orchestration) — Hook-based workflow plugin
- [GitHub Issue #4908](https://github.com/anthropics/claude-code/issues/4908) — Scoped context passing (acknowledged gap)
