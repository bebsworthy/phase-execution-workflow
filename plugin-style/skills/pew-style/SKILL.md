---
name: pew-style
description: >
  Shared design analysis methodology, token taxonomies, component role definitions, visual language scales,
  profile templates, and output formats for style migration agents.
  This skill is preloaded by all style-* agents to ensure consistent evaluation criteria.
user-invocable: true
---

# Design Language Migration Framework

## Purpose

This framework powers a multi-phase analysis of a web application's design language against a target reference (screenshots, exported source code, or both). It produces a comprehensive migration plan that maps current tokens and components to their target equivalents, proposes a semantic component hierarchy, and delivers a phased transformation roadmap.

The plugin does NOT execute changes. Its output feeds into pew-build phases for implementation.

## Tone & Approach

- Precise and visual. The audience is developers and designers.
- Every token must have an exact value (hex, px, rem) or be explicitly marked `[inferred]`.
- Use semantic naming throughout — never present a raw hex value without its role (e.g., `primary-500: #3B82F6`, not just `#3B82F6`).
- Acknowledge what the current app does well — migration preserves strengths, it doesn't start from scratch.
- Adjust depth to scale — a 5-component app doesn't need the same analysis as a 200-component design system.

---

## Input Type Handling

Agents must handle two input types transparently and mark every extracted value with its provenance:

| Input Type | Token Extraction | Component Detection | Confidence | Provenance Tag |
|------------|-----------------|---------------------|------------|----------------|
| Source code | Parse exact values from theme/config/CSS/Tailwind | Parse component definitions, props, exports | High | `[extracted]` |
| Screenshots | Visual inference from pixel analysis | Infer from visual boundaries and patterns | Medium | `[inferred]` |
| Mixed | Code for tokens, screenshots for spatial/feel | Code for structure, screenshots for visual context | High for tokens, medium for layout | Tag each value individually |

**Screenshot analysis guidance**: When analyzing screenshots, describe what you see with precision. For colors, identify the closest standard CSS named color or provide an approximate hex. For typography, describe relative scale (large heading, body text, caption) and classify serif/sans-serif/monospace. For spacing, describe as tight/comfortable/airy relative to element size.

---

## Design Token Taxonomy

All profiler agents must extract tokens organized into these categories:

### Color Tokens

| Subcategory | Description | Examples |
|-------------|-------------|---------|
| Primary | Brand color, main interactive elements | Buttons, links, active states |
| Secondary | Supporting brand color | Secondary buttons, accents |
| Accent | Highlight, attention-drawing | Badges, notifications, CTAs |
| Neutral | Grays, backgrounds, borders, text | Background, card surfaces, dividers, body text |
| Semantic | Functional meaning colors | Success (green), Error (red), Warning (amber), Info (blue) |
| Surface | Background layers | Page bg, card bg, modal bg, popover bg |
| Gradient | Multi-color transitions | Hero backgrounds, button highlights |

For each color, record: **name/role**, **value** (hex/rgb/hsl), **usage context**, **provenance tag**.

### Typography Tokens

| Subcategory | Values to Extract |
|-------------|-------------------|
| Font families | Primary (headings), secondary (body), monospace (code) |
| Size scale | Each step in the type scale with px/rem values |
| Weight scale | Available weights (100-900) and their semantic use |
| Line heights | Per size step or global defaults |
| Letter spacing | Per size step, especially headings vs body |

### Spacing Tokens

| Subcategory | Values to Extract |
|-------------|-------------------|
| Base unit | The fundamental spacing unit (4px, 8px, etc.) |
| Scale | The spacing scale steps (xs, sm, md, lg, xl, 2xl, etc.) with values |
| Component gaps | Typical gap between sibling elements |
| Section spacing | Space between major page sections |
| Padding patterns | Internal padding for cards, buttons, inputs, containers |

### Border Tokens

| Subcategory | Values to Extract |
|-------------|-------------------|
| Radius | Corner radius scale (none, sm, md, lg, full/pill) |
| Width | Border widths used (1px, 2px, etc.) |
| Style | Solid, dashed, or none — per context |
| Color | Border colors (often neutral palette) |

### Shadow Tokens

| Subcategory | Values to Extract |
|-------------|-------------------|
| Elevation scale | None, sm, md, lg, xl — with exact CSS shadow values |
| Usage pattern | Which elements are elevated (cards, modals, dropdowns, buttons) |

### Animation Tokens

| Subcategory | Values to Extract |
|-------------|-------------------|
| Duration scale | Fast (100-150ms), normal (200-300ms), slow (400-500ms) |
| Easing | Common easing functions used |
| Transition properties | Which properties are animated (opacity, transform, color, etc.) |

### Breakpoint Tokens

| Subcategory | Values to Extract |
|-------------|-------------------|
| Breakpoints | Named breakpoints with px values (sm, md, lg, xl, 2xl) |
| Strategy | Mobile-first or desktop-first |
| Container widths | Max-width at each breakpoint |

---

## Token Abstraction Layers

The industry has converged on a three-tier token architecture (aligned with the W3C Design Tokens Format Module 2025.10, Google Material Design 3, and tools like Style Dictionary). Profiler agents must classify every discovered token into one of these tiers:

| Tier | Name | Purpose | Example | W3C Mapping |
|------|------|---------|---------|-------------|
| 1 | **Primitive / Reference** | Raw values without context. Named by property + scale position. | `color-blue-500: #3B82F6`, `spacing-24: 24px` | Base tokens with `$value` |
| 2 | **Semantic / System** | Intent-driven aliases that reference primitives. Named by usage context. | `color-text-primary → color-grey-10`, `color-bg-error → color-red-100` | Alias tokens using `{group.token}` syntax |
| 3 | **Component-specific** | Scoped to individual components, referencing semantic tokens. | `button-bg-primary → color-primary-500` | Tokens within component-named groups, using `$extends` |

**Why this matters for migration**: A codebase with only tier-1 primitives needs a semantic layer built before component tokens make sense. A codebase already at tier 3 is ready for direct token swaps. The profiler's tier classification drives the migration planner's effort estimates.

**Theming capability**: Tier 2 (semantic) tokens are the key enabler for theming (light/dark modes). If the app lacks a semantic layer, the hierarchy agent should propose one as part of the migration.

---

## Token Naming Convention

Token names should follow the 4-level structure from Nathan Curtis / EightShapes, adapted to the project's context:

| Level | Purpose | Examples |
|-------|---------|---------|
| **Namespace** | System/theme/domain identifier | `ds-`, `app-`, `brand-` |
| **Object** | Component group or element (tier 3 only) | `button-`, `form-input-`, `card-` |
| **Base** | Category + property | `color-`, `spacing-`, `radius-`, `shadow-` |
| **Modifier** | Variant, state, scale, mode | `-hover`, `-500`, `-dark`, `-lg` |

Combined examples:
- Primitive: `ds-color-blue-500` (namespace + base + modifier)
- Semantic: `ds-color-text-primary` (namespace + base + context)
- Component: `ds-button-color-bg-primary-hover` (namespace + object + base + modifier)

**Rules**:
- Names must be logical, short, meaningful, and team-agreed
- Never name tokens after visual properties (`darkblue`, `largebutton`)
- Names must be searchable and filterable
- Semantic tokens describe usage, not value (`color-text-primary` not `color-grey-10-for-text`)

**Framework-first rule**: When the app uses an established component library (Ant Design, MUI, Chakra, Radix, Mantine, shadcn), its existing token naming convention takes precedence. Do not propose a custom naming scheme that conflicts with the library's token logic. Instead, extend the library's conventions where gaps exist. For example, if the app uses Ant Design's `colorPrimary` / `colorBgContainer` pattern, propose new tokens following that same camelCase convention rather than switching to kebab-case.

---

## Component Semantic Roles

Components should be classified into these standard role categories. Use these names as the canonical vocabulary when mapping between app and reference.

### Layout

| Semantic Name | Description |
|---------------|-------------|
| `PageLayout` | Top-level page wrapper (header + main + footer) |
| `Section` | Distinct content section within a page |
| `Grid` | Multi-column layout container |
| `Stack` | Vertical or horizontal flex container |
| `Container` | Max-width centered wrapper |
| `Sidebar` | Side panel layout |
| `Divider` | Visual separator between sections |

### Typography

| Semantic Name | Description |
|---------------|-------------|
| `PageTitle` | h1-level page heading |
| `SectionTitle` | h2-level section heading |
| `SectionSubTitle` | h3-level subsection heading |
| `BodyText` | Default paragraph text |
| `Caption` | Small descriptive text below elements |
| `Label` | Form field or metadata label |
| `Code` | Monospace code display |

### Data Display

| Semantic Name | Description |
|---------------|-------------|
| `Card` | Contained content block with border/shadow |
| `Table` | Tabular data display |
| `List` / `ListItem` | Ordered/unordered list with items |
| `Badge` | Small status/count indicator |
| `Avatar` | User/entity image display |
| `Stat` | Key metric with label and value |
| `Tag` | Categorization chip/pill |
| `Tooltip` | Hover-triggered contextual info |
| `EmptyState` | Placeholder when no data exists |

### Input

| Semantic Name | Description |
|---------------|-------------|
| `TextInput` | Single-line text field |
| `TextArea` | Multi-line text field |
| `Select` | Dropdown selection |
| `Checkbox` | Boolean toggle (square) |
| `Toggle` | Boolean toggle (switch) |
| `RadioGroup` | Mutually exclusive options |
| `DatePicker` | Date selection control |
| `SearchInput` | Search-specific text field |
| `FileUpload` | File selection control |

### Feedback

| Semantic Name | Description |
|---------------|-------------|
| `Toast` | Temporary notification |
| `Alert` | Persistent inline message |
| `Modal` / `Dialog` | Overlay content panel |
| `ProgressBar` | Linear progress indicator |
| `Spinner` | Loading state indicator |
| `Skeleton` | Content placeholder during load |

### Navigation

| Semantic Name | Description |
|---------------|-------------|
| `NavBar` | Primary navigation bar |
| `SideNav` | Vertical navigation list |
| `Breadcrumb` | Hierarchical location trail |
| `TabBar` | Horizontal tab navigation |
| `Pagination` | Page navigation controls |
| `MenuDropdown` | Expandable menu |

### Action

| Semantic Name | Description |
|---------------|-------------|
| `Button` | Primary/secondary/ghost/destructive action |
| `IconButton` | Icon-only action button |
| `Link` | Text navigation link |
| `DropdownMenu` | Action menu with options |
| `FloatingAction` | FAB or fixed-position action |

---

## Component Hierarchy Models

Multiple valid models exist for organizing component hierarchies. Agents should **detect which model the app currently follows** rather than forcing one:

| Model | Origin | Levels | Best For |
|-------|--------|--------|----------|
| **Atomic Design** | Brad Frost | Atoms → Molecules → Organisms → Templates → Pages | General-purpose component libraries with clear composition chains |
| **Organism-based** | Airbnb DLS | Primitives → Elements → Components (by function: Navigation, Content, Marquees, Image, Specialty) | **Domain components** — feature-specific UI grouped by business function (e.g., checkout flow, dashboard, messaging) |
| **Flat Semantic** | Shopify Polaris / this framework's role taxonomy | Single-level categories (Layout, Typography, DataDisplay, Input, Feedback, Navigation, Action) | **Shell and general UI components** — shared infrastructure like nav, layout, inputs, feedback that isn't domain-specific |

**Hybrid recommendation**: Most real-world apps benefit from combining models. Use **flat semantic** for the shared shell/infrastructure layer (design system primitives), and **organism-based** for domain-specific feature components. This prevents forcing domain components into artificial atomic layers while keeping the shared UI consistent.

**Key insight** (Brad Frost, 2025): "The specific labels have never been the point." What matters is:
1. **Dependency direction** — dependencies only flow upward (atoms never import organisms)
2. **Shared vocabulary** — the team agrees on what each level means
3. **Composition clarity** — it's obvious which components compose which

Agents should detect the app's current model, propose the best fit, and explain the mapping when the reference uses a different model.

---

## Visual Language Dimensions

Rate both the app and the reference on each dimension to characterize their visual identity:

| Dimension | Scale | Description |
|-----------|-------|-------------|
| Corner Radius | **Sharp** (0-2px) / **Subtle** (4-6px) / **Rounded** (8-12px) / **Pill** (16px+ or full) | Edge treatment |
| Elevation | **Flat** (no shadow) / **Subtle** (sm shadow) / **Elevated** (md-lg shadow) / **Floating** (xl shadow + lift) | Depth perception |
| Density | **Sparse** (>24px gaps, lots of whitespace) / **Comfortable** (12-24px) / **Compact** (4-12px) / **Dense** (<4px) | Information packing |
| Contrast | **Muted** (low contrast palette) / **Balanced** / **Bold** (strong color differentiation) / **High** (near B&W anchors) | Color intensity |
| Motion | **Static** (no animation) / **Subtle** (150ms fades) / **Moderate** (300ms transitions) / **Expressive** (500ms+ choreography) | Animation presence |
| Ornament | **Minimal** (plain, utility-first) / **Understated** (subtle borders, dividers) / **Decorated** (icons, patterns, gradients) / **Rich** (illustrations, textures, complex backgrounds) | Visual decoration level |

---

## Design Profile Template

Both `style-app-profiler` and `style-reference-profiler` MUST use this exact structure so their outputs are directly comparable section by section:

```markdown
# Design Profile: {App Name or Reference Name}

## Overview
- **Framework**: {React/Vue/Svelte/HTML}
- **Styling approach**: {Tailwind/CSS modules/styled-components/CSS vars/SCSS/mixed}
- **Design system**: {Custom/shadcn/MUI/Chakra/Radix/None detected}
- **Input type**: {codebase/screenshots/mixed}

## Visual Language Summary
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Corner Radius | {rating} | {examples} |
| Elevation | {rating} | {examples} |
| Density | {rating} | {examples} |
| Contrast | {rating} | {examples} |
| Motion | {rating} | {examples} |
| Ornament | {rating} | {examples} |

## Color Tokens
{Table: Name/Role | Value | Usage Context | Provenance}

## Typography Tokens
{Table: Level | Family | Size | Weight | Line Height | Letter Spacing | Provenance}

## Spacing Tokens
{Table: Name | Value | Usage Context | Provenance}

## Border & Radius Tokens
{Table: Name | Value | Usage Context | Provenance}

## Shadow Tokens
{Table: Name | Value | Usage Context | Provenance}

## Animation Tokens
{Table: Property | Duration | Easing | Provenance}

## Breakpoint Tokens
{Table: Name | Value | Strategy | Provenance}

## Component Inventory
{Table: Component Name | Semantic Role | Styling Mechanism | Appearance Props | File Path (if code) | Provenance}

## Token Architecture Assessment
- **Tier distribution**: {X}% primitive, {Y}% semantic, {Z}% component-scoped
- **Source of truth**: {single file / scattered}
- **Theming support**: {light/dark via semantic layer / none}
- **Design system maturity**: {0-4 level from scale}

## Component Hierarchy Assessment
- **Overall grade**: {A-F}
- **Detected model**: {Atomic Design / Organism-based / Flat Semantic / No model / Hybrid}
- **Design system maturity**: {0-4 level from scale}
- **Strengths**: {what's well-organized}
- **Weaknesses**: {ad-hoc patterns, missing abstractions}
- **Naming patterns**: {semantic vs generic}

## Ad-hoc Styling Inventory
{Table: Location | Pattern | Description | Frequency}

## Interactive Patterns
{Table: State | Implementation | Elements | Provenance}
```

---

## Migration Effort Scale

| Level | Label | Description | Typical Scope |
|-------|-------|-------------|---------------|
| L1 | Token swap | Change a CSS variable, Tailwind theme value, or theme object property | Single value, many files affected via cascade |
| L2 | Component restyle | Update one component's styles without structural change | Class changes, prop additions, style overrides |
| L3 | Component refactor | Restructure a component's markup AND styles | New props, changed DOM structure, updated tests |
| L4 | Pattern migration | Replace a styling approach for a set of components | e.g., inline styles to CSS modules across a feature |
| L5 | System overhaul | Replace the entire styling infrastructure | e.g., custom CSS to Tailwind, or build a design system from scratch |

---

## Component Hierarchy Quality Scale

| Grade | Label | Definition |
|-------|-------|-----------|
| A | Systematic | Named semantic components with consistent API, documented props, and design tokens |
| B | Mostly Semantic | Good naming for most components, some ad-hoc ones remain |
| C | Mixed | Combination of semantic components and utility/div-based constructs |
| D | Ad-hoc | Mostly inline or unsemantic styling, few reusable abstractions |
| F | Absent | No component hierarchy — page-level styling only, everything is one-off |

## Design System Maturity Model

Complements the A-F hierarchy quality grade with a broader system-level assessment (adapted from Pencil & Paper enterprise design system anatomy):

| Level | Label | Characteristics |
|-------|-------|----------------|
| 0 | None | No design system. Inline styles, no tokens, no reusable components |
| 1 | Emerging | Some shared components exist but no token system, inconsistent APIs |
| 2 | Managed | Token system in place (at least primitives), component library with basic consistency |
| 3 | Defined | Three-tier tokens (primitive + semantic + component), documented component APIs, composition patterns |
| 4 | Governed | Design-dev parity, contribution guidelines, version management, automated documentation |

Profiler agents should assign both a hierarchy grade (A-F) and a maturity level (0-4). The hierarchy grade measures component naming/structure quality; the maturity level measures overall system completeness.

---

## Correspondence Confidence Scale

| Level | Definition | Action |
|-------|-----------|--------|
| High | Same semantic role, similar visual weight, clear 1:1 mapping | Direct migration path |
| Medium | Similar role but different structure or visual treatment | Adaptation needed |
| Low | Loose analogy — roles overlap partially | Requires design decision |
| None | No counterpart in reference — app-only or reference-only component | Keep/create/remove decision by user |

---

## Conflict Classification

When the matcher detects fundamental disagreements between app and reference, flag them as:

| Type | Example | Resolution Required |
|------|---------|---------------------|
| **Layout** | Sidebar nav vs top nav, single-page vs multi-page | User must choose direction |
| **Theme** | Dark-first vs light-first, high contrast vs muted | User must choose direction |
| **Density** | Dense data tables vs spacious cards | User must set target density |
| **Navigation** | Tab-based vs drawer-based, breadcrumbs vs back buttons | User must choose pattern |
| **Interaction** | Click-to-expand vs hover-to-reveal, modal vs inline editing | User must choose pattern |

Mark conflicts in correspondence output as `[CONFLICT: {type}]` for orchestrator to detect.

---

## Semiotic Basis for Cross-Domain Matching

Component matching across different domains is grounded in semiotic theory from HCI research. This section provides the theoretical framework that the matcher agent uses.

**Core principle** (Saussure): UI elements gain meaning through **opposition and context within a sign system**, not through inherent properties. A "primary button" means "main action" because it contrasts with "secondary button" and "ghost button" — this oppositional relationship holds regardless of domain.

**Semiotic Engineering** (De Souza): Interfaces are metacommunication artifacts — the designer communicates to users "how, when, where, and why" to interact. When matching across domains, match by **what the designer is communicating** (intent), not by what the component contains (content).

**Three sign classes** in UI (relevant to component matching):

| Sign Class | UI Manifestation | Matching Implication |
|-----------|-----------------|---------------------|
| **Static** | Layout position, color, typography, iconography | Match by visual role and position in hierarchy |
| **Dynamic** | Animations, transitions, multi-step interactions | Match by behavior pattern (expand, dismiss, navigate) |
| **Metalinguistic** | Tooltips, help text, onboarding overlays | Match by the relationship to the sign they explain |

**Practical matching heuristic**: Two components across different domains are semantically equivalent when they:
1. Occupy the same position in their respective **sign opposition systems** (primary vs secondary, prominent vs subtle)
2. Serve the same **communicative function** (call to action, data display, navigation affordance, status feedback)
3. Create similar **user expectations** through semiotic convention (card = contained content, red = danger, elevation = interactivity)

**Domain-specific semiotics warning**: Some sign conventions are domain-specific and should NOT be migrated blindly. For example:
- Medical/health: red may indicate blood/vitals, not errors
- Finance: green/red indicate gain/loss, not success/error
- Maps: colors indicate geography, not UI semantics

The matcher agent should flag domain-specific semiotic conflicts separately from structural conflicts.

---

## Interface Inventory Completeness Checklist

Profiler agents should verify coverage across all these categories (from Brad Frost's interface inventory methodology) to ensure no component type is missed:

1. **Global elements** — header, footer, global navigation, skip links
2. **Navigation** — primary nav, secondary nav, breadcrumbs, pagination, tabs
3. **Image handling** — avatars, thumbnails, heroes, galleries, responsive images
4. **Icons** — icon system, icon sizes, icon colors, icon-only buttons
5. **Forms** — inputs, selects, checkboxes, radio buttons, validation states, labels, fieldsets
6. **Buttons** — primary, secondary, ghost, destructive, icon buttons, button groups, sizes
7. **Headings** — h1-h6 usage, heading hierarchy, display headings
8. **Blocks** — cards, heroes, feature sections, testimonials, banners, callouts
9. **Lists** — data lists, navigation lists, definition lists, ordered/unordered
10. **Interactive** — accordions, tabs, modals, tooltips, dropdowns, popovers, drawers
11. **Media** — video players, audio players, embeds, iframes
12. **Third-party** — ads, analytics widgets, embedded content, chat widgets
13. **Typography** — body text, links, emphasis, code blocks, blockquotes, captions
14. **Colors** — full palette, semantic usage, gradients, opacity patterns
15. **Animations** — transitions, loading states, micro-interactions, skeleton screens

If a category has no components, explicitly note it as "Not present" rather than omitting it.

---

## Workspace Structure

All style analysis output goes to a project-scoped directory:

```
style/{project_name}/
  01-intake.json              # Input classification & scope
  02-app-profile.md           # App design token inventory & component map
  03-reference-profile.md     # Reference design profile (same template)
  04-correspondence.md        # Semantic matching & token delta
  05-hierarchy.md             # Component hierarchy proposal & design system definition
  06-migration-plan.md        # Phased migration roadmap
  report.md                   # Synthesized final report
  .meta.json                  # Run metadata (timestamps, input hashes, re-run detection)
```

---

## Completion Signals

All style-* agents must end their output with:

```
[style-{name}] COMPLETE ✓ -- saved to style/{project}/{output-file}
```

If the agent encounters issues that don't prevent completion but need attention:

```
[style-{name}] COMPLETE WITH NOTES ✓
NOTES:
1. {note}
2. {note}
```
