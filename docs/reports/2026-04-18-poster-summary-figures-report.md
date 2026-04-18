# Poster Summary Figures Report

> This report packages a 4-panel poster layout with two large main figures and two smaller reflection-evolution figures.

## Core Message

- ExpeL degrades under website drift.
- Reflection stays stronger on newer websites and transfers better to held-out validation task sets.
- Reflection rule iteration is real, but not monotonic.

## 4-panel poster layout

- Left column: two larger main panels.
- Right column: two smaller `Reflection Rules on Website V3` panels.
- Use big labels and keep spoken explanation short.

## Training Task Sets

![Training Task Sets Main](../../figures/training_task_sets_main_poster_summary.svg)

![Training Task Sets Reflection V3](../../figures/training_task_sets_reflection_v3_poster_summary.svg)

On training task sets, ExpeL rules help dramatically on the original environment but collapse on the harder vibe-coded Website V3, while reflection rules remain strong across newer website versions.

| Website Version | No Rules | ExpeL Rules | Best Reflection Rules |
| --- | ---: | ---: | ---: |
| Website V1 | 9/68 (13.2%) | 56/68 (82.4%) | N/A |
| Website V2 | N/A | 60/68 (88.2%) | 67/68 (98.5%) |
| Website V3 | N/A | 8/68 (11.8%) | 65/68 (95.6%) |

## Held-out Validation Task Sets

![Held-out Validation Task Sets Main](../../figures/heldout_validation_task_sets_main_poster_summary.svg)

![Held-out Validation Task Sets Reflection V3](../../figures/heldout_validation_task_sets_reflection_v3_poster_summary.svg)

On held-out validation task sets, ExpeL rules degrade sharply as the website changes, while reflection rules transfer better to unseen tasks and remain stronger on both vibe-coded versions.

| Website Version | No Rules | ExpeL Rules | Best Reflection Rules |
| --- | ---: | ---: | ---: |
| Website V1 | 133/167 (79.6%) | 124/167 (74.3%) | N/A |
| Website V2 | N/A | 114/167 (68.3%) | 143/167 (85.6%) |
| Website V3 | N/A | 66/167 (39.5%) | 97/167 (58.1%) |

## Short script

- Start with the orange line: ExpeL drops as the website changes.
- Then point to the blue bars: reflection remains stronger on newer websites.
- Finally point to the right-side panels: later reflection versions are not always better.
