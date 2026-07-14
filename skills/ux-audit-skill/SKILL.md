---
name: ux-audit
description: Produce a structured UX audit of a digital product (website, application, B2B platform) from screenshots, URLs, or both. Grounds findings in UX and product frameworks (Nielsen, Shneiderman, Norman, Gestalt, Kano, service design, North Star metrics). Supports English, Turkish, and German output. Includes optional market and competitor benchmarking. Use this skill whenever a user wants a UX review, heuristic evaluation, expert design review, usability audit, or structured critique of a product's user experience — even if they don't explicitly say "audit". After producing the written audit, hand off to the ux-audit-deck skill to generate a presentation deck if the user wants one.
---

# UX Audit

Produce a structured UX audit in the methodology of Başak Akbulak. The audit is a written report grounded in cognitive and behavioral principles, structured around specific findings with severity tags, and optionally includes market and competitor benchmarking.

This skill handles Phase 1: the written audit. When the user wants a presentation deck at the end, hand off to the `ux-audit-deck` skill by loading its SKILL.md.

## Method — five core components

**1. Modular scope.** The audit rests on three legs: issues found in the product itself, benchmarks from the market that frame what's possible, and behavioral/research grounding that helps the client make strategic decisions. Depth scales to project size; structure stays constant.

**2. Two-pass walkthrough.** Analyze in two modes. First as a novice user encountering the product for the first time — what feels off, where friction appears, where the eye gets lost. Then as an expert applying frameworks — name what you noticed, attach diagnoses, cite the principle that explains why the issue matters. Novice pass produces the *signal*, expert pass produces the *explanation*.

**3. Audience-aware severity.** Severity tagging is itself a UX decision about the audit document. For action-forcing reports to senior stakeholders, use clear tags (Major / Mid / Minor). For internal product teams who need to discuss rather than receive verdicts, soften — drop tags or use `?` on items that need stakeholder input rather than a fix. Default to Major / Mid / Minor unless the user signals a different audience.

**4. Benchmarks as ideation seeds.** When referencing benchmark examples, the purpose isn't "you're behind the market." It's "here's raw material to seed redesign thinking." Pick examples for generative variety, not closest comparison.

**5. Cross-domain transposition.** When direct competitors aren't accessible (closed B2B, niche verticals), match by user behavior pattern rather than industry category. Ask what other products solve a similar user mental state, not what other products are in the same vertical.

## Flow — three questions before context

Ask these three questions in order at the start. Each one shapes downstream behavior.

### Step 1 — Language

Ask (verbatim, all three languages together):

> **Which language would you like the audit in? / Raporu hangi dilde hazırlamamı istersiniz? / In welcher Sprache möchten Sie das Audit?**
> - English
> - Türkçe
> - Deutsch

All subsequent output — questions, findings, labels, framework names — stays in the chosen language. Never mix.

For language-specific severity tags, section labels, and framework name translations, read `references/language_labels.md`.

### Step 2 — Mode

Ask which mode. Full user-facing menu text with constraint disclosures is in `references/mode_menus.md`. Read that file and present the menu in the chosen language.

Three modes:
- **Screenshots** — visual analysis. Recommended default.
- **URLs only** — structural analysis via `web_fetch`. No visual insight.
- **Hybrid** — URLs + screenshots paired per page.

If the user picks URLs only or Hybrid for a closed B2B product, gently suggest Screenshots might serve them better. Accept their answer either way.

### Step 3 — Benchmarking

Ask (in chosen language):

> **Should this audit include a benchmarking section?**
> - **Market only** — how the wider sector approaches similar user problems. Wide-angle patterns and conventions.
> - **Competitors only** — how specific direct competitors solve these problems. Feature parity, differentiators, common vs. rare patterns.
> - **Both** — market patterns and named competitors, with comparison back to the audited product.
> - **None** — skip benchmarking entirely.

If the user picks Competitors or Both, ask two follow-ups:
1. Whether they have specific competitors in mind or want you to suggest them.
2. Whether they can share competitor screenshots. Include this framing: *"This is optional but strongly recommended. A benchmark slide with an actual screenshot of the competitor's interface is significantly more useful than a text description — designers pattern-match on layout, not on prose. Without screenshots, the benchmark section will still work but be text-only."*

If the user picks Market or Both, ask what sector to use as the frame.

**Benchmark research protocol:** draft from training data first, then validate with web search before finalizing. Specific queries ("Cuvva car insurance app features 2026", not "insurance apps"). Update or remove claims that can't be confirmed. Cite sources for anything specific (features, market share, launch dates). Never invent competitor features.

## Context gathering

After language, mode, and benchmarking selection, ask for context in the chosen language:

- Product name and category (required)
- Target users — **optional**. If not provided, proceed and add a note in the audit cover: *"Target users were not specified. Findings are based on inference; a follow-up with defined user personas would sharpen some observations."*
- Audience for the audit (optional — affects severity tagging tone)
- Scope (optional)
- Known constraints — legal, technical, business (optional)

Then, per mode:
- **Screenshots:** ask for labeled or numbered screenshots.
- **URLs only:** ask for a URL list, then fetch each with `web_fetch`. If a page returns empty / auth-walled / SPA shell, stop and tell the user explicitly — offer to skip, retry, or switch to Screenshots for that page.
- **Hybrid:** URLs + screenshots paired per page.

Ask one focused question per gap rather than a long list. Don't guess.

## Frameworks — grounding library

For the diagnostic frameworks (Nielsen's 10 heuristics, Shneiderman's rules, Norman's principles, Gestalt, cognitive load, WCAG), product frameworks (Kano, service design, North Star / OKRs), and research methods (card sorting, tree testing, A/B, usability testing, etc.), read `references/frameworks.md`.

**Citation rules:**
- Framework citation is **encouraged but not required**. Cite when it genuinely explains why users behave a certain way or when it strengthens the finding. Skip when citing would feel forced or decorative — some findings are observational and don't need a heuristic to justify their existence.
- Cite by name and number ("Nielsen #6 (Recognition rather than recall)"), not paraphrase. Use the framework's terminology in the chosen language.
- One framework reference per finding is the norm. Multiple only when reinforcing different aspects of the same issue.
- Don't cite a framework you can't defend in one sentence.

## Producing the written audit

### Cover section

- Product name and description
- Pages reviewed (list explicitly)
- Target users (or the not-specified note)
- Severity tally
- **Mode indicator** (required): one line stating which mode was used and what it covers. Examples:
  - Screenshots: *"Mode: Visual audit (screenshots). Covers visual hierarchy, layout, attention flow, and interaction patterns."*
  - URLs only: *"Mode: Structural audit (URLs). Covers IA, content hierarchy, copy, link structure. Visual hierarchy and interaction issues are out of scope for this review."*
  - Hybrid: *"Mode: Combined (URLs + screenshots). Covers structural and visual analysis together."*
- **Benchmark scope** (if benchmarking selected): one line indicating what was benchmarked.

### Findings

Order Major → Mid → Minor → open questions. Each finding contains:

- **Severity tag** (language-appropriate — see language_labels.md)
- **Short finding title** — ≤36 chars total including the tag. This is a hard limit imposed by the presentation deck's slide title placeholder in Phase 2. Even if the user only wants the written audit, keep the title tight — it forces clarity. Examples of good titles: `#Major — Two-basket problem`, `#Mid — Fulfillment dominates PDP`.
- **Finding.** One or two paragraphs. Describe the user's likely experience, not the design's intent. Number sub-points inline if the finding has multiple parts.
- **Heuristic** (optional, encouraged where it strengthens the finding).
- **Solution or Suggestions** — pick per-finding:
  - **Solution** when the finding has a clear right answer (Fitts's law violation with an obvious fix, a WCAG failure with one correct answer).
  - **Suggestions** when the finding opens 2–3 legitimate paths with different trade-offs. Label alternatives I, II, III and describe what each optimizes for.
  - Default to Suggestions when uncertain — presenting alternatives is safer than prescribing a fix the audit can't fully defend from screenshots alone.
- **Strategic frame** (optional): North Star / OKR mapping or service-design framing where relevant.
- **Suggested research** (optional): research method recommendation, with one line on what it would surface. Only include when validation would meaningfully change the design decision — not as decoration.
- **Evidence reference** — mode-dependent: `Screenshot 2 — basket page`, `URL: https://...`, or both for Hybrid.
- **Optional idea** prefixed `IDEA:`.

For examples of well-formed findings (structure, tone, framework grounding, suggestions with trade-offs), read `references/calibration_examples.md`.

### Benchmarking section (if selected)

Placed *after* findings, before the closing. Structure varies by user's selection:

**Market only:** describe 3–5 dominant patterns in the specified sector. For each:
- Name the pattern
- Kano tier (basic / performance / delight)
- Comparison to the audited product: matches, exceeds, or falls short?
- If it falls short, is that a deliberate positioning choice or an unaddressed gap?

**Competitors only:** for each named competitor (user-provided or Claude-suggested and validated):
- What the competitor does
- 2–4 notable UX patterns from their product
- Kano tier for each
- Comparison to the audited product: similarities, differences, gaps, unique advantages

**Both:** market section first (wide angle), then competitor section (specific), then a synthesis paragraph identifying which competitor patterns represent broad market moves vs. unique differentiators.

Whichever variant is used, end with a *"What to steal, what to ignore"* paragraph — applying cross-domain transposition to identify which competitor patterns match the audited product's user behavior and which don't.

## Mode-specific quality rules

- **URL-only mode:** findings must be derivable from page source. Allowed grounding: IA, navigation depth, heading hierarchy, content density, copy clarity, link patterns, semantic structure, WCAG semantic criteria. Not allowed: visual hierarchy, color, weight, attention flow. If you find yourself writing "the primary CTA isn't visually dominant" in URL-only mode, stop — you can't see that.
- **Hybrid mode:** findings are strongest when structural and visual evidence disagree. Example: *"The H1 reads 'Trekkingschuh Röti III' but the visual focal point is the yellow price burst — the structural and visual hierarchies contradict."*
- **Screenshots mode:** full framework library available.

## Constraints

- **Never invent details not in the evidence** (screenshots or fetched content). Hallucinated UI details destroy credibility.
- **Never invent competitor features.** Validate before including.
- **Don't over-claim.** When something needs research to validate, say so ("worth testing with users") rather than asserting it as fact.
- **Don't generate generic findings.** "The navigation could be improved" is useless. Every finding must be specific to what's actually shown, with a specific user behavior implication and a specific suggestion.
- **Don't pad.** A 5-finding audit where each is tight beats a 15-finding audit padded with obvious points.
- **Paraphrase, don't quote.** When referencing competitor or benchmark examples, paraphrase what they do — don't reproduce copy verbatim.

## Handoff to deck generation

After delivering the written audit, ask the user (in chosen language): *"Ready to generate the presentation, or do you want to revise any findings first?"*

If they want the deck, load `ux-audit-deck/SKILL.md` (the sibling skill) and follow its instructions. Pass along the full written audit — findings, benchmarks, mode, language, all context — as the input to Phase 2.

If they want to revise first, iterate on the findings, then loop back to this handoff.

## Reference files

Load these when needed — don't preload:

- **`references/language_labels.md`** — severity tags, section labels, and framework name translations across English, Turkish, and German. Load once at the start of an audit and reference throughout.
- **`references/mode_menus.md`** — full user-facing text of the Screenshots / URLs / Hybrid menu in three languages, with constraint disclosures.
- **`references/frameworks.md`** — the full grounding library (Nielsen, Shneiderman, Norman, Gestalt, cognitive load, WCAG, Kano, service design, North Star, research methods) with translations.
- **`references/calibration_examples.md`** — examples of well-formed findings showing the target structure, tone, and depth of framework grounding.
