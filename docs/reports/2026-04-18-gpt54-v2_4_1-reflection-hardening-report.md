# GPT-5.4 V2.4.1 Reflection Hardening Report

## API smoke status
- Provider usable: `True`
- Generation endpoint: `responses_stream`
- Models available: `True`
- Response excerpt: `OK`
- Compatibility note: ASXS was usable in this run, but only after using curl-like request headers and falling back to /responses streaming. The provider returned HTTP 200 with empty text for chat_completions, responses_json before the streaming fallback produced usable content.

## Focus20 transition counts
- `both_success`: 65
- `lost`: 2
- `saved`: 0
- `both_fail`: 1

Transition explanations:
- `old success -> new success`: preserve these successful V2.4 behaviors when drafting v2.4.1 rules.
- `old success -> new fail`: treat these as regression evidence that the candidate must repair without overfitting.

## TaskBank36 held-out summary
- `both_success`: 89
- `lost`: 54
- `saved`: 8
- `both_fail`: 16

## v2.4 -> v2.4.1 rule delta summary
- Edited rules: 2
- Added rules: 0
- Dropped rules: 0
- Proposal accepted/rejected: 2/2
- Evidence mode: `transition_casebook_fallback`
- Required gap phrases: login next, filtered bookmark, final answer

Preserve patterns:
- Preserve successful v2.4 behavior that logs in once and lets the existing same-site next redirect land on the protected destination with its original query intact.
- Preserve URL/query-based completion detection for navigation-only and filtered bookmark tasks so the agent stops once the requested state is clearly visible.
- Preserve the broader anti-loop behavior: after failed clicks or hidden targets, switch strategy instead of repeating stale bids.

Lost patterns:
- Hardv3 loses the login next redirect after successful authentication by overwriting a task-specific filtered bookmark destination with an unrelated generic/probe route.
- Hardv3 keeps acting after target evidence is already visible, especially when a filtered bookmark URL or destination page is already loaded, instead of giving the final answer.
- Existing rules cover tagged add-bookmark next preservation, but the current gap shows missing cross-task coverage for login next preservation to filtered bookmark destinations and other protected in-site routes.

Changed rules:
- `Finalize instead of noop when URL, query, or heading already proves the target state` -> `Finalize instead of acting when URL, query, heading, or redirected destination already proves completion`
- `Preserve task-specific login next parameters and never replace them with generic examples` -> `Preserve task-specific login next destinations and their query parameters across authentication`

Focus20 lost-case excerpt:
## Representative `lost` Excerpts
- task 1600303 (`content` / `lost`)
  left: step 0 action=fill('39', 'baseline') url=http://127.0.0.1:49904/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=- | step 1 action=fill('42', 'Baseline123!') url=http://127.0.0.1:49904/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=-
  right: step 0 action=fill('42', 'baseline') url=http://127.0.0.1:29404/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=- | step 1 action=fill('45', 'Baseline123!') url=http://127.0.0.1:29404/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=-

## Verification
- Verification ok: `True`
- Verification skipped: `False`
- Focus20 coverage: `68/68 covered`
