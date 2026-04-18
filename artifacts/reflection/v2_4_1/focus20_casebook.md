# focus20 Casebook

## Transition Legend
- `both_success`: old success -> new success
- `lost`: old success -> new fail
- `saved`: old fail -> new success
- `both_fail`: old fail -> new fail

## Transition Counts
- `both_fail`: 1
- `both_success`: 65
- `lost`: 2

## Top Behavior Gaps

## Representative `both_success` Excerpts
- task 973001 (`access` / `both_success`)
  left: step 0 action=fill('40', 'baseline') url=http://127.0.0.1:49703/login/ error=- final=- | step 1 action=click('44') url=http://127.0.0.1:49703/login/ error=- final=-
  right: step 0 action=click('42') url=http://127.0.0.1:29203/login/ error=- final=- | step 1 action=fill('47', 'baseline') url=http://127.0.0.1:29203/login/ error=- final=-
- task 973801 (`access` / `both_success`)
  left: step 0 action=fill('40', 'baseline') url=http://127.0.0.1:49703/login/?next=/bookmarks/new error=- final=- | step 1 action=click('44') url=http://127.0.0.1:49703/login/?next=/bookmarks/new error=- final=-
  right: step 0 action=click('42') url=http://127.0.0.1:29203/login/?next=/bookmarks/new error=- final=- | step 1 action=fill('47', 'baseline') url=http://127.0.0.1:29203/login/?next=/bookmarks/new error=- final=-
- task 1600101 (`access` / `both_success`)
  left: step 0 action=fill('40', 'baseline') url=http://127.0.0.1:49703/login/?next=/settings error=- final=- | step 1 action=click('44') url=http://127.0.0.1:49703/login/?next=/settings error=- final=-
  right: step 0 action=click('42') url=http://127.0.0.1:29203/login/?next=/settings error=- final=- | step 1 action=fill('47', 'baseline') url=http://127.0.0.1:29203/login/?next=/settings error=- final=-

## Representative `lost` Excerpts
- task 1600303 (`content` / `lost`)
  left: step 0 action=fill('39', 'baseline') url=http://127.0.0.1:49904/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=- | step 1 action=fill('42', 'Baseline123!') url=http://127.0.0.1:49904/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=-
  right: step 0 action=fill('42', 'baseline') url=http://127.0.0.1:29404/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=- | step 1 action=fill('45', 'Baseline123!') url=http://127.0.0.1:29404/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=-
- task 1600307 (`functional` / `lost`)
  left: step 0 action=fill('39', 'baseline') url=http://127.0.0.1:50102/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=- | step 1 action=fill('42', 'Baseline123!') url=http://127.0.0.1:50102/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=-
  right: step 0 action=fill('42', 'baseline') url=http://127.0.0.1:29602/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=- | step 1 action=fill('45', 'Baseline123!') url=http://127.0.0.1:29602/login/?next=%2Fbookmarks%3Fq%3Dfocus20-login-filter error=- final=-
