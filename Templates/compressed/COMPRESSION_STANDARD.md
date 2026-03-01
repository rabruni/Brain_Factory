# LLM Template Compression Standard

## Purpose
Agents consume `Templates/compressed/` instead of `Templates/`. Same information, ~73% fewer tokens. Humans author and review `Templates/` (full). Agents read `Templates/compressed/`.

## When to Use
- Agents: ALWAYS read from `compressed/`. Never load full templates into agent context.
- Humans: ALWAYS read/edit `Templates/` (full). Compressed versions are derived, not authored.
- Sync: When a full template changes, re-compress it using the rules below.

## Compression Rules (in order of application)

### 1. Comments: delete or promote
If a `<!-- comment -->` contains a RULE (count, ordering, mandatory item), promote it to a one-line constraint. If it's explanation of what a section IS, delete — the LLM knows from the heading.

### 2. N examples → 1 pattern
Replace N placeholder instances with one pattern description. Two example articles with `[placeholder]` fields → one line: `Per article, ALL FOUR required: Rule | Why | Test | Violations`.

### 3. Prose → predicate
"One paragraph explaining why this rule exists. What goes wrong if it's violated?" → `one paragraph, what breaks if violated`. Cut adjectives and connectors that don't change meaning.

### 4. Formatting: strip
Horizontal rules, decorative blank lines, repeated markdown chrome. LLMs parse semantically, not visually.

### 5. Deduplicate
If heading and comment say the same thing, keep one. If a table header explains what column items say, keep the header.

### 6. Vocabulary: preserve
Domain terms, proper nouns, technical identifiers (SC-NNN, CLR-NNN, FMWK-001), MUST/MUST NOT language. These are the highest-density tokens. Never compress these.

### 7. Relationships: preserve
Dependencies, ordering constraints, cross-references, gate conditions. Structural rules survive intact.

### 8. Omit implied knowledge
If the LLM already knows it (how to number sequentially, what markdown tables look like, what "required" means), don't teach it.

## The Principle
> Strip everything the LLM can reconstruct from context. Preserve everything it can't.

Reconstructable: formatting, placeholder examples, explanatory prose, "how to fill this out" instructions.
Not reconstructable: domain vocabulary, counts, orderings, cross-references, your specific constraints.

## Verification Method
After compressing, test: use ONLY the compressed version to generate real output for a concrete component. Audit against the original template's required sections checklist. If anything is missing, that rule was load-bearing — restore it.

## File Inventory
Every file in `Templates/` has a compressed counterpart in `Templates/compressed/` with the same filename.
