# Calibration examples — what "good" looks like

Reference examples of well-formed findings. Use these to calibrate structure, tone, framework grounding, and the depth of suggestions.

The signature of a good finding: a designer reading it thinks *"yes, that's a real issue I would have flagged, the framework citation is honest, the suggestions are three real paths not one dressed-up option, and the research would actually answer the question that separates them."* — not *"this is generic AI output with random framework name-drops."*

## Example 1 — Major finding with Suggestions and strategic frame (English, Screenshots mode)

**#Major — Two-basket problem**

**Heuristic:** Nielsen #4 — Consistency and standards. Standard e-commerce flows resolve fulfillment at checkout, not upstream. The two-basket pattern departs from a near-universal convention, forcing users to relearn the purchase flow.

**Finding:** The business depends on both delivery and pick-up, but having two separate baskets is hard to navigate. Most e-commerce sites use a single basket where fulfillment details are resolved during purchase. Two baskets degrades the experience for two reasons:

1. Users can't focus on the decision to purchase right away — they have to think about how they want to receive the product before they've even committed.
2. Users change their minds constantly and rarely make these decisions in a focused environment. Two baskets means doubling the cognitive load and repeating actions across both flows.

**Suggestions:**
- *I. Unified basket with per-line fulfillment toggle.* Single basket page, each line item has a Pickup/Deliver switch. Optimizes for user cognitive simplicity.
- *II. Unified basket with mode split at checkout review.* Single basket, allocation surfaced at the order-review step. Optimizes for the current mental model with less structural change.
- *III. Keep two baskets, add bridging.* If two-basket architecture is non-negotiable, add cross-basket reminders and one-click move actions. Lowest engineering cost, highest ongoing friction.

**Strategic frame:** Directly affects the platform's North Star (successful mixed-order checkouts per week). Suggestion I most likely to move the metric; suggestion III leaves it flat.

**Suggested research:** Tree testing with 30–50 LANDI customers comparing the current two-basket flow vs. suggestion I. Surface: which path lets users complete a mixed-order task with fewer errors and shorter time-to-checkout.

**Evidence reference:** Screenshot 4 — basket overview page.

## Example 2 — Mid finding with Solution (English, Screenshots mode)

**#Mid — Price hidden by promotional overlay**

**Heuristic:** F-pattern scanning (A5). Users skim product listing pages in an F-pattern, focusing on top-left text elements and skimming rightward. Text embedded in imagery (like a yellow price burst overlaid on the product photo) is read as decoration and skipped by the eye.

**Finding:** Prices on the product listing page are rendered as yellow bursts overlaid on the product image rather than as clean text elements near the product name. Users scanning the grid to compare products effectively lose the single most important piece of information — the price — because it's visually camouflaged as promotional imagery.

**Solution:** Render prices as bold text directly under the product title. Reserve the yellow-burst styling exclusively for actual promotional markdowns (percentage off, "sale" tags), so the burst becomes a genuine signal rather than the default treatment.

**Evidence reference:** Screenshot 3 — product listing page.

## Example 3 — Minor finding without heuristic citation (English, Screenshots mode)

**#Minor — Continue shopping link is low-weight**

**Finding:** On the basket page, the "Continue shopping" link sits at low visual weight against the primary "Order now" CTA. This is technically the correct hierarchy — you want conversion to dominate — but the current implementation puts the link so far below the fold and in such muted styling that users who realize they want to add one more item have to hunt for it. The result is either abandoned baskets (they give up and lose their selection) or a broken navigation loop (they use the browser back button, which sometimes reloads the basket empty).

**Suggestions:**
- *I.* Keep the current styling but relocate the link above the basket contents, adjacent to the basket total.
- *II.* Add a small "+ Add another item" secondary button next to the primary CTA in the same visual cluster.

**Evidence reference:** Screenshot 4 — basket overview page.

*(Note: no heuristic cited here. The finding is observational — a low-weight link causing hunt-and-peck behavior. Citing Nielsen #7 or Fitts's law would be forced. The finding stands on its own.)*

## Example 4 — Turkish, URL-only mode

**#Önemli — Ana navigasyon başlıkları özensiz**

**Sezgisel kural:** Nielsen #2 (Sistemin gerçek dünya ile eşleşmesi). Navigasyon başlıkları kullanıcıların tanıdığı doğal kelimelerden çok, iç departman isimlerinden türetilmiş — kullanıcı zihinsel modeli ile sistem hiyerarşisi eşleşmiyor.

**Tespit:** Ana menüde "Ürün Yönetimi", "Süreç Modülleri" ve "Sistem Yapılandırma" gibi başlıklar kullanılıyor. Bu terimler kuruluşun iç yapısını yansıtıyor olabilir ancak son kullanıcı bu isimlerin arkasında hangi işlevlerin bulunduğunu tahmin etmek zorunda kalıyor. Sitede geçirilecek zaman, hedefi bulma süresinden çok, terimleri deşifre etmeye ayrılıyor olabilir.

**Öneriler:**
- *I.* Görev odaklı bir dile geçin — "Ürün Yönetimi" yerine "Ürünlerinizi yönetin", "Sistem Yapılandırma" yerine "Ayarlar" gibi.
- *II.* Mevcut başlıkları koruyun ama her birinin altına, kullanıcının o alanda ne yapabileceğini açıklayan kısa bir alt metin ekleyin.

**Önerilen araştırma:** Ağaç testi (C2) — mevcut başlıklar ve önerilen yeni dil ile 20-30 kullanıcı üzerinde. Ölçüm: doğru hedefe ulaşma oranı ve karar süresi.

**Kanıt referansı:** URL: https://example.com/panel

## Example 5 — German, Hybrid mode with disagreement between structural and visual evidence

**#Mittel — Semantische und visuelle Hierarchie widersprechen sich**

**Heuristik:** Gestalt (Kontinuität) und Konsistenz zwischen Codestruktur und visueller Präsentation.

**Befund:** Der HTML-Quelltext kennzeichnet den Produktnamen als H1 ("Trekkingschuh Röti III") — semantisch die primäre Überschrift der Seite. Visuell jedoch dominiert ein großer gelber Preis-Burst ("99.95") das Blickfeld und zieht die Aufmerksamkeit als erstes Element auf sich. Nutzer, die schnell durch mehrere Produktseiten scrollen, nehmen den Preis als visuelle Marke wahr, während der Produktname im Hintergrund verschwindet — obwohl die technische Hierarchie das Gegenteil beabsichtigt. Für Screenreader-Nutzer und SEO ist die Hierarchie korrekt; für sehende Nutzer ist sie umgekehrt.

**Vorschläge:**
- *I.* Visuelle Hierarchie an die semantische anpassen: Produktname als große Überschrift, Preis als bold Text darunter, gelber Burst nur bei tatsächlichen Rabatten.
- *II.* Semantische Hierarchie an die visuelle anpassen: den Preis als H1 kennzeichnen, den Produktnamen als H2 — nur wenn dies eine bewusste Geschäftsentscheidung ist (etwa bei einer Discount-Retail-Positionierung).

**Beleg:** URL: https://landi.ch/shop/trekking-arbeitsschuhe + Screenshot 2 — Produktdetailseite

*(Note: this finding is strongest because it draws on both sources of evidence and cites a genuine contradiction between them.)*
