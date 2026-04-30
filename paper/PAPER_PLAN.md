# WebCoEvo Paper Upgrade Plan

## Title

WebCoEvo: Adversarial Co-Evolution for Web-Agent Reflection Rules: Capability-Targeted Website Drift on Linkding

## Claim-Evidence Matrix

| Claim | Evidence | Paper Location |
| --- | --- | --- |
| ExpeL task-experience rules help on the original Linkding control site but are not robust to hardv3 website drift. | Control Focus20 improves from 9/68 to 56/68 with ExpeL; hardv3 ExpeL-only falls to 8/68 on Focus20 and 66/167 on TaskBank36. | Abstract, Introduction, Results |
| Compact cross-version reflection rules recover much of the hardv3 loss. | V2.4 reaches 65/68 on Focus20 hardv3 and 97/167 on TaskBank36 hardv3. | Results, Discussion |
| Rule iteration is evidence-driven but not monotonic. | V2.4.1 edits two V2.4 rules from transition evidence, ties V2.4 on TaskBank36, but trails V2.4 on Focus20. | Methodology, Results |
| The standalone WebCoEvo runner makes rule injection auditable. | Traces separate injected ExpeL rule ids from cross-version reflection rule ids and record rulebook paths, selection context, misses, and reset-time errors. | Methodology, Experimental Setup |

## Section Plan

1. Introduction: motivate website drift as an adaptive benchmark-design problem and state upgraded results.
2. Related Work: position against static web benchmarks, web evolution, adaptive environment generation, and reflection rules.
3. Methodology: describe the WebCoEvo loop, runner, website taxonomy, rulebooks, and evaluation protocol.
4. Linkding Experimental Setup: define Focus20, TaskBank36, website suites, prompt conditions, and provenance.
5. Results: report control, first-modified, hardv3, and V2.4.1 transition findings.
6. Discussion and Conclusion: state rule-refinement, environment-hardening, and cross-site transfer implications.
7. Appendix: list local artifacts, full hardv3 tables, taxonomy, and claim boundary.

## Figure/Table Plan

- Figure 1: Website-version success summary for Focus20 and TaskBank36.
- Figure 2: Hardv3 per-drift success matrix for Focus20 and TaskBank36.
- Appendix Table 1: Source report/artifact notes.
- Appendix Tables 2-3: Full hardv3 per-drift counts.
- Appendix Table 4: Drift taxonomy definitions.
