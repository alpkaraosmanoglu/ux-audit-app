# Frameworks — grounding library

Frameworks are load-bearing evidence, not decoration. Use them when they earn their place; skip them when citing would be forced.

## A. Diagnostic frameworks — for grounding findings

### A1. Nielsen's 10 Usability Heuristics

The most commonly cited framework. Language translations are in `language_labels.md`.

1. **Visibility of system status** — keep users informed about what's happening through appropriate, timely feedback.
2. **Match between system and the real world** — speak users' language with familiar words, phrases, and concepts. Follow real-world conventions and make information appear in natural order.
3. **User control and freedom** — users often perform actions by mistake. Provide clearly marked emergency exits, undo, redo.
4. **Consistency and standards** — users shouldn't have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions.
5. **Error prevention** — prevent problems from occurring. Eliminate error-prone conditions, or check for them and present a confirmation before commitment.
6. **Recognition rather than recall** — minimize memory load by making objects, actions, and options visible. The user shouldn't have to remember information from one part of the interface to another.
7. **Flexibility and efficiency of use** — accelerators (invisible to novices) speed up interaction for experts. Allow users to tailor frequent actions.
8. **Aesthetic and minimalist design** — every extra unit of information competes with the relevant units of information and diminishes their relative visibility.
9. **Help users recognize, diagnose, and recover from errors** — error messages in plain language, precisely indicating the problem and constructively suggesting a solution.
10. **Help and documentation** — easy to search, focused on the user's task, list concrete steps to be carried out.

### A2. Shneiderman's 8 Golden Rules

1. Strive for consistency
2. Seek universal usability (cater to diverse users, novice to expert)
3. Offer informative feedback
4. Design dialogs to yield closure
5. Prevent errors
6. Permit easy reversal of actions
7. Keep users in control (internal locus of control)
8. Reduce short-term memory load

### A3. Norman's design principles

From *The Design of Everyday Things*. Translations in `language_labels.md`.

- **Affordances** — properties of an object that suggest how it can be used.
- **Signifiers** — perceptible cues that reveal affordances.
- **Feedback** — communication of the results of an action.
- **Mapping** — the relationship between controls and their effects.
- **Constraints** — restricting the interaction possibilities to prevent error.
- **Conceptual model** — the user's mental model of how the system works.
- **Discoverability** — can users figure out what's possible.

### A4. Gestalt principles of visual perception

Use for visual-hierarchy findings.

- **Proximity** — elements close together are perceived as related.
- **Similarity** — elements sharing visual attributes are perceived as related.
- **Continuity** — the eye follows the smoothest path through a design.
- **Closure** — the brain fills in gaps to perceive complete shapes.
- **Figure-ground** — the brain separates foreground from background.
- **Common region** — elements within a bounded area are perceived as grouped.
- **Symmetry** — symmetrical elements are perceived as unified.

### A5. Cognitive load and attention

- **Miller's law** — working memory holds roughly 7±2 items (treated more conservatively today as 3–5).
- **Hick's law** — decision time scales logarithmically with the number of choices.
- **Fitts's law** — time to acquire a target depends on distance to the target and its size.
- **Goal-gradient effect** — motivation increases as people approach a goal (relevant for checkout flow design, progress indicators).
- **F-pattern and Z-pattern reading** — attention flow in latin-reading regions. F-pattern for content-heavy pages, Z-pattern for lighter marketing-style layouts.

### A6. WCAG (Web Content Accessibility Guidelines)

Cite specific success criteria when accessibility is in scope. Common examples:
- **1.4.3 Contrast (Minimum)** — text must have contrast ratio of at least 4.5:1
- **2.4.4 Link Purpose (In Context)** — links must be understandable from their text or context
- **3.3.2 Labels or Instructions** — form fields need labels or instructions

## B. Product and service frameworks

### B1. Kano model

Categorizes product features by user response.

- **Basic (must-have / thresholds)** — expected features. Absence causes dissatisfaction, presence causes no positive reaction. Example: e-commerce checkout that works reliably.
- **Performance (linear / one-dimensional)** — satisfaction scales linearly with quality. Example: faster page load, more search results.
- **Delight (excitement / attractive)** — unexpected features. Presence delights, absence goes unnoticed. Example: an insurance app that auto-generates trip coverage from calendar data.

Use Kano to organize competitor benchmarking. For each competitor pattern, label whether it's basic (table stakes), performance (linear satisfaction), or delight (unexpected). This lets the audit distinguish "you're missing baseline features" from "here are creative differentiators to consider."

### B2. Service design frameworks

- **Service blueprint** — maps user actions, front-stage touchpoints, back-stage processes, and support systems for a full service flow. Use when the audit spans multiple channels or the digital product is part of a larger service (call centers, physical stores, human handoffs).
- **Front-stage / back-stage** — separates what the user sees from what the organization does behind the scenes. Findings that touch back-stage (data quality, integration lag, human process) belong here rather than in pure UX.
- **Moments of truth** — the specific interactions that disproportionately shape user perception. Use to prioritize which findings deserve highest attention.
- **Touchpoint map** — the sequence of contact points between user and organization across a service journey.

### B3. North Star Metric and OKRs

- **North Star Metric** — the single user-centric metric that best captures the product's core value delivery. Example: "successful mixed-order checkouts per week" for a retail platform. Frame high-severity findings in terms of how they push or pull the North Star.
- **OKRs (Objectives and Key Results)** — objectives are qualitative goals; key results are quantitative signals. Use when the audit's audience is a product team or leadership who need to see findings mapped to measurable outcomes.

When findings map cleanly to a North Star or OKR (e.g., "this friction directly reduces the % of users who complete their primary job"), name that mapping. It gives the audit business teeth without being decorative.

## C. Research methods — for solution validation

Only recommend by name when validation would meaningfully change the design decision. Translations in `language_labels.md`.

- **C1. Card sorting** — surfaces how users mentally group content. Use for IA, taxonomy, navigation labeling.
- **C2. Tree testing** — validates whether an existing or proposed IA lets users find what they need. Often paired with card sorting.
- **C3. First-click testing** — surfaces whether the page's visual hierarchy directs users toward the right first action.
- **C4. Five-second test** — surfaces what users remember and infer about a page after brief exposure. Validates value-prop clarity and visual hierarchy.
- **C5. A/B testing** — quantitatively compares variants on a metric. Use when there's a clear hypothesis and enough traffic.
- **C6. Moderated usability testing** — observes users completing tasks while thinking aloud. Surfaces the *why* behind friction. Small N (5–8 users) catches most issues.
- **C7. Unmoderated remote testing** — faster, cheaper, lower-fidelity than moderated. Good for validating specific flows.
- **C8. Qualitative interviews** — surfaces user mental models, context, goals, frustrations. Use upstream of design decisions.
- **C9. Diary studies** — longitudinal context, surfaces patterns that emerge over time. Use for products people interact with repeatedly.
- **C10. Heatmap and session recording analysis** — passive observation of real users at scale. Surfaces where attention actually falls vs. designer intent.
- **C11. Competitive heuristic review** — apply framework A across direct competitors to benchmark common patterns. Note: this is auditing, not user research.

## Citation examples

- EN: *"This violates Nielsen #6 (Recognition rather than recall) — users must remember basket contents from a previous page rather than seeing them surfaced."*
- TR: *"Bu, Nielsen #6 (Hatırlamak yerine tanıma) ilkesini ihlal ediyor — kullanıcı önceki sayfadaki sepet içeriğini hatırlamak zorunda."*
- DE: *"Dies verletzt Nielsen #6 (Erkennen statt Erinnern) — Nutzer müssen den Warenkorbinhalt der vorherigen Seite abrufen."*

Bad citation examples (avoid):
- Vague name-drops without a defensible mechanism: ~*"This violates general usability principles."*~
- Wrong principle: citing Fitts's law when the issue is memory-related, not target-acquisition.
- Multiple citations when one would do: ~*"This violates Nielsen #6, Miller's law, Norman's mapping principle, and WCAG 2.4.4."*~ Pick the one that most precisely fits.
