# Poster Summary Figures Design

**Goal:** Design two poster-ready summary figures that explain how rule-based guidance behaves as Linkding websites drift from the original environment to vibe-coded variants, while separating training-like and held-out validation task sets.

**Audience:** Poster viewers who have very little patience for internal rulebook naming such as `v2.4`, `v2.5`, or `v2.6`.

**Primary communication constraint:** The figures must be understandable without explaining internal version IDs. Public-facing labels should therefore use:

- `Website V1`, `Website V2`, `Website V3`
- `Reflection Rules V1`, `Reflection Rules V2`, `Reflection Rules V3`, `Reflection Rules V4`
- `Training Task Sets`
- `Held-out Validation Task Sets`

---

## Narrative Goal

The two figures should jointly communicate three claims:

1. As the website changes from the original environment to vibe-coded variants, `ExpeL Rules` lose robustness, especially on the harder `Website V3`.
2. `ExpeL Rules` help a lot on the original training-like environment, but they do not reliably transfer to held-out validation tasks; `Reflection Rules` are stronger on newer vibe-coded websites and generalize better.
3. `Reflection Rules` can be iterated from `V1` to `V4`, but later iterations are not guaranteed to be stronger than earlier ones.

The figures should make claims `1` and `2` the main visual story. Claim `3` should appear as a compact inset so the main chart stays readable from poster distance.

---

## Final Figure Pair

The poster should use two figures placed left-to-right:

1. **Left figure:** `Training Task Sets`
2. **Right figure:** `Held-out Validation Task Sets`

Both figures should share the same visual grammar, legend order, and public labels.

---

## Recommended Visual Structure

Each figure should use a **bar + line hybrid** with a small inset.

### Main plot

- **X-axis:** website version
  - `Website V1`
  - `Website V2`
  - `Website V3`
- **Y-axis:** success rate (`0%` to `100%`)
- **Bars:** within-version method comparison
- **Lines:** across-version method trajectory

### Inset

- Small panel in the upper-right corner of each figure
- Title: `Reflection Rules on Website V3`
- Content: four bars or lollipops for `Reflection Rules V1/V2/V3/V4`
- Purpose: show that reflection-rule iteration is real, but not monotonic

---

## Why This Layout

This layout makes each claim legible at poster scale:

- **Bars** answer: “Which method is stronger on this website version?”
- **Lines** answer: “How does the same method change as the website drifts?”
- **Inset** answers: “Does iterating reflection rules always help?”

This is better than a pure grouped bar chart because the across-version degradation of `ExpeL Rules` becomes much easier to see. It is also better than putting all reflection versions into the main chart, which would make the poster too dense.

---

## Public Label Mapping

Do not show internal names such as `v2.4`, `v2.5`, `v2.6`, or `v2.4.1` in the main poster figures.

Use this mapping in figure captions or appendix text only:

- `Reflection Rules V1` = internal `v2.4`
- `Reflection Rules V2` = internal `v2.5`
- `Reflection Rules V3` = internal `v2.6`
- `Reflection Rules V4` = internal `v2.4.1`

Use this website mapping in the figure body:

- `Website V1` = original Linkding `1.45.0`
- `Website V2` = first vibe-coded website version
- `Website V3` = harder vibe-coded website version

---

## Figure 1: Training Task Sets

### Title

`Training Task Sets`

### Subtitle

`Performance across website versions`

### Main plot series

For the main plot, use:

- `No Rules` at `Website V1` only
- `ExpeL Rules` at `Website V1`, `Website V2`, `Website V3`
- `Best Reflection Rules` at `Website V2`, `Website V3`

The main figure should not show all four reflection versions directly. It should only show the best completed reflection result at each website version:

- `Website V2`: `Best Reflection Rules = Reflection Rules V1`
- `Website V3`: `Best Reflection Rules = Reflection Rules V1`

### Training data to encode

| Website Version | No Rules | ExpeL Rules | Best Reflection Rules |
| --- | ---: | ---: | ---: |
| `Website V1` | `9/68 = 13.2%` | `56/68 = 82.4%` | N/A |
| `Website V2` | N/A | `60/68 = 88.2%` | `67/68 = 98.5%` |
| `Website V3` | N/A | `8/68 = 11.8%` | `65/68 = 95.6%` |

### Training inset data

`Reflection Rules on Website V3`

| Reflection Version | Success Rate |
| --- | ---: |
| `Reflection Rules V1` | `65/68 = 95.6%` |
| `Reflection Rules V2` | `60/68 = 88.2%` |
| `Reflection Rules V3` | `60/68 = 88.2%` |
| `Reflection Rules V4` | `60/68 = 88.2%` |

### Intended takeaway

The training-like figure should visually say:

- `ExpeL Rules` deliver a huge gain over `No Rules` on the original environment.
- `ExpeL Rules` remain competitive on `Website V2`, but collapse on `Website V3`.
- `Best Reflection Rules` remain strong on both `Website V2` and `Website V3`.
- Reflection-rule iteration exists, but the first reflection version remains strongest on this benchmark.

### Recommended one-sentence caption

`On training task sets, ExpeL rules help dramatically on the original environment but collapse on the harder vibe-coded Website V3, while reflection rules remain strong across newer website versions.`

---

## Figure 2: Held-out Validation Task Sets

### Title

`Held-out Validation Task Sets`

### Subtitle

`Transfer to unseen task sets across website versions`

### Main plot series

Use the same series structure as the left figure:

- `No Rules` at `Website V1` only
- `ExpeL Rules` at `Website V1`, `Website V2`, `Website V3`
- `Best Reflection Rules` at `Website V2`, `Website V3`

For the main figure, the public-facing best reflection series should be:

- `Website V2`: `Best Reflection Rules = Reflection Rules V1`
- `Website V3`: `Best Reflection Rules = Reflection Rules V1 / V4 tie`

Since ties are hard to show cleanly in the main plot, the bar can use the shared best value and the tie should be explained in the inset or caption.

### Held-out validation data to encode

| Website Version | No Rules | ExpeL Rules | Best Reflection Rules |
| --- | ---: | ---: | ---: |
| `Website V1` | `133/167 = 79.6%` | `124/167 = 74.3%` | N/A |
| `Website V2` | N/A | `114/167 = 68.3%` | `143/167 = 85.6%` |
| `Website V3` | N/A | `66/167 = 39.5%` | `97/167 = 58.1%` |

### Held-out validation inset data

`Reflection Rules on Website V3`

| Reflection Version | Success Rate |
| --- | ---: |
| `Reflection Rules V1` | `97/167 = 58.1%` |
| `Reflection Rules V2` | `61/167 = 36.5%` |
| `Reflection Rules V3` | `82/167 = 49.1%` |
| `Reflection Rules V4` | `97/167 = 58.1%` |

### Intended takeaway

The held-out figure should visually say:

- On the original validation environment, `ExpeL Rules` do not outperform `No Rules`.
- As the website changes from `Website V1` to `Website V3`, `ExpeL Rules` degrade substantially.
- `Best Reflection Rules` outperform `ExpeL Rules` on both vibe-coded website versions.
- Reflection-rule iteration is not monotonic, but the strongest reflection variants still generalize better than `ExpeL Rules`.

### Recommended one-sentence caption

`On held-out validation task sets, ExpeL rules degrade sharply as the website changes, while reflection rules transfer better to unseen tasks and remain stronger on both vibe-coded versions.`

---

## Exact Chart Geometry

Both figures should use the same geometry.

### Main panel

- One wide plotting area per figure
- Three grouped x-axis positions: `Website V1`, `Website V2`, `Website V3`
- At `Website V1`, show two bars:
  - `No Rules`
  - `ExpeL Rules`
- At `Website V2` and `Website V3`, show two bars:
  - `ExpeL Rules`
  - `Best Reflection Rules`

### Overlaid lines

- Orange line: connect `ExpeL Rules` bars from `Website V1 -> V2 -> V3`
- Blue line: connect `Best Reflection Rules` bars from `Website V2 -> V3`

These lines should use filled markers centered on the bar tops. The line should not be drawn through `Website V1` for reflection, because that method is not part of the current evaluation there.

### Inset

- Place in the upper-right corner inside each figure
- Rough size: `25%` to `30%` of the main figure width
- Use a simple four-bar chart
- Add a small note:
  - Training panel: `Not monotonic: V1 remains best`
  - Held-out panel: `Not monotonic: V1 and V4 tie`

---

## Color and Style

Use a small, poster-friendly palette:

- `No Rules`: light gray `#b8bec7`
- `ExpeL Rules`: warm orange `#d97706`
- `Best Reflection Rules`: strong blue `#2563eb`

Inset bars for reflection evolution:

- `Reflection Rules V1`: dark blue
- `Reflection Rules V2`: medium blue
- `Reflection Rules V3`: lighter blue
- `Reflection Rules V4`: blue with dark outline

Highlight the best inset bar(s) with a dark stroke and bold value label.

### Typography

- Keep titles short and large
- Use sentence-case subtitles
- Avoid parentheses-heavy labels
- Always show success rate values on or above bars

### Poster-readability rule

If a label requires explaining internal jargon while standing at the poster, the label is too technical and should be simplified.

---

## Annotations to Include

Each figure should include one short annotation near the steepest important change.

### Training figure annotations

- Near `Website V1`, annotate:
  - `Large gain from rules on the original environment`
- Near `Website V3` on the orange series, annotate:
  - `ExpeL collapses on the hardest vibe-coded website`

### Held-out figure annotations

- Near `Website V1`, annotate:
  - `ExpeL does not beat No Rules here`
- Near `Website V3`, annotate:
  - `Reflection remains clearly above ExpeL`

These annotations should be short enough to read in under two seconds.

---

## Speaker Notes for Poster Use

These figures are meant to support a short spoken explanation:

1. `On the original training-like website, ExpeL helps a lot.`
2. `But when the website is vibe-coded into V2 and especially V3, ExpeL becomes much less stable.`
3. `Reflection rules are more robust on the changed websites, and they transfer better to held-out validation tasks.`
4. `We can iterate reflection rules from V1 to V4, but later iterations are not automatically better, which is why the inset is important.`

If the presenter only has ten seconds per figure, these are the intended one-line summaries:

- Training: `ExpeL helps on the original site, but reflection stays stronger once the website changes.`
- Held-out: `Reflection generalizes better than ExpeL on unseen validation tasks under website drift.`

---

## What To Avoid

Do not use the following in the main poster figures:

- internal labels such as `v2.4`, `v2.5`, `v2.6`, `v2.4.1`
- raw benchmark names such as `Focus20` or `TaskBank36` in the titles
- more than three main methods in a single website-version group
- seven-drift breakdowns inside the same poster summary figure
- long explanatory legends that compete with the data

These belong in appendix figures, backup slides, or nearby text, not in the main poster summary visual.

---

## Recommended Caption Pair

### Left figure

`Training task sets across website versions. ExpeL rules provide a large gain over no rules on the original website, but reflection rules remain stronger once the website is changed into vibe-coded versions. The inset shows that reflection-rule iteration is real but not monotonic.`

### Right figure

`Held-out validation task sets across website versions. ExpeL rules degrade as the website changes and do not consistently beat the no-rules baseline, while reflection rules transfer better to unseen validation tasks. The inset shows that later reflection iterations are not guaranteed to be better, even though the strongest reflection variants still outperform ExpeL.`

---

## Data Sources

The design above is grounded in these current summaries:

- [2026-04-18-umich-qwen3-rule-comparison-report.md](/home/gecm/WebCoEvo/docs/reports/2026-04-18-umich-qwen3-rule-comparison-report.md)
- [2026-04-18-website-version-line-report.md](/home/gecm/WebCoEvo/docs/reports/2026-04-18-website-version-line-report.md)
- [2026-04-17-hardv3-xvr-matrix-report.md](/home/gecm/WebCoEvo/docs/reports/2026-04-17-hardv3-xvr-matrix-report.md)

If the underlying benchmark numbers change, the visual structure should stay the same and only the plotted values and captions should be refreshed.
