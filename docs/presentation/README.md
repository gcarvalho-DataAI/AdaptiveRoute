# Presentation

Two renderings of the same deck (17 slides), for a mixed technical/stakeholder audience.

| File | Use |
| --- | --- |
| `adaptiveroute_slides.pdf` | Projection and hand-off. Compiled from the `.tex` source. |
| `adaptiveroute_slides.tex` | Beamer source for the PDF. |
| `adaptiveroute_deck.html` | Browser deck. Open directly, no build step. |
| `img/` | Product screenshots used by both renderings. |

`img/` holds `admin-dashboard.png` and `route-chat.png` — real captures of the running app,
referenced by relative path from both the HTML and the `.tex`. Keep the folder next to the deck
files or both builds lose their images.

## Rebuilding the PDF

```bash
cd docs/presentation
pdflatex -interaction=nonstopmode adaptiveroute_slides.tex
```

Requires a LaTeX distribution with `beamer`, `booktabs`, `colortbl`, `helvet` and `tikz`.
A single pass is sufficient — the deck has no cross-references or table of contents.

## The HTML deck

Open `adaptiveroute_deck.html` in any browser.

- `←` `→`, space, or PageUp/PageDown to navigate; `Home` / `End` to jump to either end.
- `N` toggles the speaker-notes drawer; `Esc` closes it.
- Swipe on touch devices.
- `#7` in the URL opens slide 7 directly; the current slide is kept in the address bar.

## Speaker notes

Slides carry the claim; the detail lives in speaker notes. Seven slides have them — 3, 7, 9, 10,
12, 13 and 14 — and both renderings hold the same text.

In the HTML deck press `N`. For the PDF, change one line at the top of the `.tex`:

```latex
\setbeameroption{show notes}   % was: hide notes
```

and rebuild — that produces 21 pages (each annotated slide followed by its notes page) instead of 14.
Keep it on `hide notes` for the version you project.

## Visual identity

Both renderings use the product's own design system, lifted from
[frontend/src/styles.css](../../frontend/src/styles.css) so the deck and the app read as one thing:

| Token | Value | Use |
| --- | --- | --- |
| Background | `#050914` with blue/green radial washes | canvas |
| Text / muted / faint | `#edf3f8` · `#9aaec5` · `#62748c` | copy hierarchy |
| Accent | `#5b8def` · `#9fc0ff` | eyebrows, links, active nodes |
| Signature gradient | `#6bb6ff → #58ddb0` | brand mark, pills, progress, stat numbers |
| Green / amber / danger | `#4fd1a1` · `#e1ad58` · `#f97066` | solver authority, warnings, failure |

Typography is Inter with tight negative tracking on headings, matching the app's `.topbar h1`.
Panels reuse the app's rounded-corner, bordered, subtly-filled card treatment.

If the frontend palette changes, update the `:root` block in the HTML deck and the
`\definecolor` block in the `.tex` — they are the only two places colours are declared.

## Content

| Slides | Arc |
| --- | --- |
| 1–4 | Problem, tension, design thesis |
| 5–8 | Two-model split, architecture, cascade, validation contract |
| 9–10 | The product, running |
| 11–13 | Training, results, measured limits |
| 14–17 | Engineering, known limits, next steps, close |

### The two-model claim

The deck distinguishes two LLMs with separate jobs, mirroring the `.env` split between
`ADAPTIVEROUTE_ORCHESTRATOR_*` and `ADAPTIVEROUTE_ROUTING_POLICY_*`:

- **Qwen2.5-Coder-32B** — orchestrator. Off the shelf, temperature 0.1. Reads the driver's message,
  extracts the event, answers route questions.
- **Qwen2.5-7B + LoRA v5** — routing policy. Fine-tuned, temperature 0. Emits the stop sequence.

Keep this distinction intact when editing: the 94.4% feasibility figure describes the **routing
policy only**, and the deck scopes it that way deliberately. A screenshot in slide 10 shows the
32B's model id in the execution trace, so a vague claim would be visibly contradicted on screen.

Figures in the deck are drawn inline (TikZ in the PDF, SVG in the HTML) — there are no
external image assets to keep in sync.

Numbers come from [EVALUATION.md](../EVALUATION.md), [MODEL_DECISION.md](../MODEL_DECISION.md)
and [MODEL_CAPACITY_BENCHMARK.md](../MODEL_CAPACITY_BENCHMARK.md). Update those first, then
the two deck sources.
