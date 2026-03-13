---
name: pew-ux-audit
description: >
  Shared audit methodology, severity scales, and output format for UX audit agents.
  This skill is preloaded by all ux-audit-* agents to ensure consistent output.
user-invocable: true
---

# UX Auditor Framework

## Purpose

This framework powers a 5-phase UX/UI audit that traces every finding back to a user goal. It goes beyond usability checklists to evaluate whether an application is **beautiful, enjoyable, and efficient** — covering emotional design, cognitive science, content quality, trust, and delight alongside traditional heuristics and accessibility.

Subjective aesthetic opinions with no functional justification are not findings. Every finding must connect to a user goal or a violated principle with documented evidence.

## Tone & Approach

- Direct and precise. Do not soften findings.
- Every section must have a verdict: ✅ Solid, ⚠️ Needs Work, or ❌ Critical.
- **Call out strengths**: Note what is done well, not just violations. This builds credibility and adoption.
- Every finding must trace to a user goal (Job ID from Phase 1).
- Findings that affect accessibility or dark patterns are exceptions — they are always critical regardless of job traceability.

---

## Severity Scale (Enhanced Baymard/Nielsen Model)

Each finding is scored on two dimensions:

**Impact** (how much it harms the experience when encountered):

| Score | Meaning |
|-------|---------|
| **0** | Not a usability problem |
| **1** | Cosmetic problem only — fix if time permits |
| **2** | Minor problem — low priority fix |
| **3** | Major problem — important to fix |
| **4** | Usability catastrophe — must fix before release |

**Frequency** (how often users encounter the problem):

| Score | Meaning |
|-------|---------|
| **4** | Always — every user hits this in every session |
| **3** | Often — majority of users encounter this regularly |
| **2** | Sometimes — encountered in 25–75% of sessions |
| **1** | Rarely — edge case or uncommon path |

**Overall Severity** = (Impact + Frequency) / 2, rounded up.

When frequency data is unavailable, default to Impact score alone and note "frequency unobserved."

## Improvement Level Scale

| Level | Type | Description | Typical Effort |
|-------|------|-------------|----------------|
| L1 | Atomic change | Single copy, color, or label change | < 1 hour |
| L2 | Component fix | Style, state, or behaviour change within one component | Hours |
| L3 | Pattern introduction | Adding or replacing an interaction pattern within one flow | 1–3 days |
| L4 | Flow redesign | Restructuring the step sequence for a complete user job | 1–2 weeks |
| L5 | Structural redesign | Rethinking IA, navigation architecture, or core mental model | 2–6 weeks |

## Priority Buckets

| Bucket | Severity | Effort | Action |
|--------|----------|--------|--------|
| **Quick Wins** | High (3–4) | Low (L1–L2) | Do first — highest ROI |
| **Strategic investments** | High (3–4) | High (L4–L5) | Plan and schedule |
| **Easy improvements** | Low (1–2) | Low (L1–L2) | Batch with regular work |
| **Defer or deprioritise** | Low (1–2) | High (L4–L5) | Validate need before investing |

## Kano Classification

Tag every proposal with its Kano category to capture the emotional dimension of prioritization:

| Category | Definition | User Reaction if Present | User Reaction if Absent |
|----------|------------|-------------------------|------------------------|
| **Basic** | Must-have — expected by default | No satisfaction increase | Strong dissatisfaction |
| **Performance** | More is better — linear satisfaction | Proportional satisfaction | Proportional dissatisfaction |
| **Delighter** | Unexpected joy — non-linear satisfaction | Disproportionate delight | No dissatisfaction |

Quick Wins that are **Basic** needs should be prioritized above Quick Wins that are **Performance** needs. **Delighters** should be sprinkled into every phase — they drive retention and word-of-mouth.

---

## Research Source Hierarchy

When citing evidence, always reference the tier:

| Tier | Source Type | Examples |
|------|------------|---------|
| 1 — Primary research | Empirical, peer-reviewed, large-sample studies | Nielsen Norman Group, Baymard Institute, CHI papers, WCAG 2.2 |
| 2 — Expert synthesis | Thought leaders with documented experience | Don Norman, Steve Krug, Luke Wroblewski, Jared Spool, Aarron Walter |
| 3 — Practitioner case studies | Design system rationale docs | Shopify Polaris, Apple HIG, Material Design 3, Fluent |
| 4 — Pattern libraries | Catalogued interaction patterns | UI-Patterns.com, Mobbin, Page Flows, Laws of UX |
| 5 — Competitive observation | Market leader analysis | Manual walkthroughs of direct and adjacent competitors |

Do not cite opinion articles, listicles, or unattributed "best practice" claims.

---

## Cognitive Science Laws

Apply these systematically during audit layers that evaluate task flows and visual design.

### Fitts's Law — Target Acquisition

Time to reach a target = f(distance to target + size of target). Larger, closer targets are faster to hit.

**Audit checklist:**
- Primary action targets: >= 48px on mobile (Apple HIG), >= 32px on desktop
- Primary CTAs positioned for thumb reach on mobile (bottom half of screen)
- Distance between frequently-used controls minimized
- Destructive actions physically separated from primary actions

### Hick's Law — Decision Time

Decision time increases logarithmically with the number of choices. More options = slower decisions.

**Audit checklist:**
- Primary options per screen: <= 5–7 (use progressive disclosure for more)
- Navigation menu depth: <= 3 levels before reaching goal
- Smart defaults provided to reduce decision burden
- Recommended/suggested options highlighted to guide choice

### Miller's Law — Working Memory

Users can hold 7 +/- 2 items in working memory. Exceeding this causes cognitive overload.

**Audit checklist:**
- Form fields per visible screen: <= 5 (or grouped into labelled sections)
- List items visible before scroll: <= 7–9
- Wizard/stepper phases: chunked into logical groups of 3–5 steps
- Information required from memory (not shown on screen) minimized

### Norman's Feedback Timing Thresholds

| Threshold | User Perception | Design Requirement |
|-----------|----------------|-------------------|
| < 100ms | Feels instant | No indicator needed |
| 100–300ms | Slight delay perceived | Subtle visual feedback (button state change) |
| 300–1000ms | System is working | Loading indicator required |
| > 1000ms | Context switch risk | Progress indicator + keep user informed |
| > 10s | High abandonment risk | Background processing + notification on completion |

---

## Gestalt Principles

Evaluate visual perception and grouping. These determine whether the interface "makes sense" at a glance.

| Principle | Definition | What to Audit |
|-----------|------------|---------------|
| **Proximity** | Elements close together are perceived as related | Are related controls/info grouped? Do unrelated items touch? |
| **Similarity** | Same color/shape/size = related | Do same-function elements look identical? Are categories visually distinct? |
| **Figure-Ground** | Foreground vs. background clarity | Can users distinguish content from chrome? Is contrast sufficient? |
| **Closure** | Brain completes incomplete shapes | Do icons/skeleton loaders communicate effectively? |
| **Continuity** | Eyes follow smooth lines/paths | Do visual flows guide users naturally through the page? |
| **Common Region** | Enclosing borders suggest grouping | Are cards, containers, sections used effectively (not overused)? |
| **Symmetry** | Balance implies completeness | Is layout balanced? Does asymmetry serve purpose or feel accidental? |

Score each 0–3: 0 = violated, 1 = inconsistent, 2 = adequate, 3 = deliberately applied.

---

## Emotional Design Framework (Don Norman)

Every interface operates on three levels simultaneously. A great product excels at all three.

### Visceral Level (Pre-conscious — first 50ms)
First impression. Does the product look trustworthy, professional, and appropriate for its domain?
- Color palette appropriateness (warm/cool for context)
- Typography personality (does it match the product's character?)
- Visual polish and attention to detail
- Appropriate use of imagery and whitespace

### Behavioral Level (Subconscious — during use)
Does using the product feel efficient, responsive, and predictable?
- Task efficiency and flow
- Responsiveness and feedback quality
- Error handling and recovery
- Micro-interaction satisfaction

### Reflective Level (Conscious — after use)
Does the product reinforce the user's identity and values? Is it memorable?
- Does the product tell a coherent story?
- Do users feel pride or ownership using it?
- Is the brand voice consistent across all touchpoints?
- Would users recommend it based on how it makes them feel?

Score each level 0–4. **Note contradictions** between levels (e.g., visceral polish at 4 but behavioral frustration at 1 = uncanny valley).

---

## Micro-Interaction Quality Framework (Dan Saffer)

Evaluate interactive elements on four dimensions:

| Dimension | Definition | What to Audit | Scoring |
|-----------|------------|---------------|---------|
| **Trigger** | What initiates the interaction | Is it discoverable? Clear affordance? | 0 = invisible, 1 = hard to find, 2 = obvious, 3 = delightfully signaled |
| **Rules** | What happens during the interaction | Is behaviour predictable? Consistent? | 0 = broken, 1 = unpredictable, 2 = predictable, 3 = intuitive |
| **Feedback** | What the system communicates | Visual/audio response? Within 100–300ms? | 0 = none, 1 = minimal, 2 = present, 3 = clear and satisfying |
| **Loops & Modes** | Repetition and state management | Can users repeat? Is state persistent? | 0 = broken, 1 = works once, 2 = repeatable, 3 = remembers + adapts |

Apply to: buttons, form inputs, navigation, modals, notifications, drag interactions, scrolling behaviors.

---

## Content Quality Framework

Evaluate all user-facing copy across these dimensions:

| Dimension | What to Audit | Scoring |
|-----------|---------------|---------|
| **Clarity** | Can users understand at a glance? Avg sentence length, jargon, passive voice | 0 = incomprehensible, 1 = dense, 2 = clear enough, 3 = scannable |
| **Consistency** | Same action = same label everywhere? Tone uniform? | 0 = chaotic, 1 = some patterns, 2 = mostly consistent, 3 = intentional voice |
| **Persuasiveness** | CTAs action-oriented? Error messages helpful? Copy drives desired behavior? | 0 = unhelpful, 1 = generic, 2 = functional, 3 = motivating |
| **Microcopy** | Placeholders, error messages, success confirmations, empty states, loading text | 0 = missing, 1 = generic, 2 = helpful, 3 = personality-driven |

**Key evaluation points:**
- Error messages: Do they name the problem AND suggest a fix?
- CTAs: verb + noun ("Save changes") vs. generic ("Submit")?
- Empty states: educational and actionable, or just "No data"?
- Labels: match user vocabulary (from Phase 1) or internal terminology?
- Tone: consistent across the entire application?

---

## Trust & Credibility Framework (NNG Research)

Users form credibility judgments in ~50ms, primarily from visual design.

| Factor | Weight | What to Audit |
|--------|--------|---------------|
| **Design quality** | ~46% | Does the product look polished, professional, and trustworthy? |
| **Information design** | ~28% | Are navigation labels clear? Is information complete and transparent? |
| **Connection to broader web** | ~15% | External links to authorities? Privacy/security badges? Social proof? |
| **Performance & responsiveness** | ~11% | Does the product feel fast and reliable? No broken links or errors? |

Score each factor 0–3: 0 = actively harms trust, 1 = basic, 2 = professional, 3 = premium/sophisticated.

---

## Dark Pattern Detection

Dark patterns are manipulative design choices that benefit the business at the user's expense. Each detected pattern is automatically Severity 4.

| Pattern | Definition | What to Look For |
|---------|------------|-----------------|
| **Forced continuity** | Auto-renewing subscriptions without clear notice | Hidden renewal terms, difficult cancellation |
| **Hidden costs** | Extra charges revealed late in flow | Fees appearing at checkout, mandatory add-ons |
| **Confirm-shaming** | Guilt-tripping users into accepting | "No thanks, I don't want to save money" |
| **Trick questions** | Confusing opt-in/opt-out language | Double negatives, pre-checked boxes |
| **Roach motel** | Easy to get in, hard to get out | Easy signup, buried cancellation/deletion |
| **Misdirection** | Drawing attention away from important info | Visual emphasis on upsell, de-emphasis on costs |
| **Sneak into basket** | Adding items without consent | Pre-selected add-ons in cart |
| **Obstruction** | Making a process unnecessarily difficult | Multi-step cancellation, required phone calls |

---

## Design System Maturity Assessment

| Dimension | What to Audit | Scoring |
|-----------|---------------|---------|
| **Component coverage** | % of UI built with system components vs. custom one-offs | 0 = ad-hoc, 1 = <25%, 2 = 25–75%, 3 = >75% |
| **Token consistency** | Colors, spacing, typography drawn from a defined scale? | 0 = no tokens, 1 = partial, 2 = mostly consistent, 3 = systematic |
| **Interactive states** | All components define hover, focus, active, disabled, loading, error? | 0 = none, 1 = some, 2 = most, 3 = all states defined |
| **Documentation** | Are patterns, tokens, and usage guidelines documented? | 0 = none, 1 = minimal, 2 = partial, 3 = comprehensive |
| **Accessibility built-in** | Do components include ARIA, keyboard handling, contrast by default? | 0 = none, 1 = ad-hoc, 2 = partial, 3 = systematic |

---

## Findings Registry Format

Every finding in the final registry must use this format:

| ID | Audit Layer | Finding | Framework Reference | Severity (0–4) | Frequency (1–4) | Job ID | Kano | Recommended Pattern |
|----|-------------|---------|---------------------|----------------|-----------------|--------|------|---------------------|

Finding ID format: `F-NNN` (sequential across all phases).

---

## JTBD Statement Template

> **When** [situation / trigger], **I want to** [motivation / action], **so I can** [expected outcome / progress].

Every job has three dimensions:

| Dimension | Question |
|-----------|----------|
| **Functional** | What task needs to be completed? |
| **Emotional** | How does the user want to feel? |
| **Social** | How does the user want to be perceived? |

### Outcome Statements (ODI — Ulwick)

For each JTBD, define 5–8 desired outcomes using this template:

> **Minimize** the time/likelihood/effort it takes to [desired outcome].

Example outcomes for "filter articles by topic":
- Minimize the time it takes to identify relevant articles
- Minimize the number of clicks to apply a filter
- Minimize the likelihood of missing important articles
- Minimize the effort to understand which filters are active

### Demand-Side Forces (Moesta)

For each JTBD, document the four forces that drive adoption:

| Force | Direction | Question |
|-------|-----------|----------|
| **Push of situation** | Toward change | What problems with current solutions drive the user to seek alternatives? |
| **Pull of idea** | Toward change | What attracts the user to this product specifically? |
| **Habit of present** | Against change | What inertia keeps the user with their current approach? |
| **Anxiety of change** | Against change | What concerns prevent the user from fully switching? |

---

## File-Saving Instructions

1. Write your complete output to your designated file under `ux-review/`.
2. Do not write to any other agent's file.
3. Signal completion with: `[AGENT-ID] COMPLETE ✓ — saved to ux-review/<filename>`
