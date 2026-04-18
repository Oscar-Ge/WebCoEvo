# taskbank36 Casebook

## Transition Legend
- `both_success`: old success -> new success
- `lost`: old success -> new fail
- `saved`: old fail -> new success
- `both_fail`: old fail -> new fail

## Transition Counts
- `both_fail`: 16
- `both_success`: 89
- `lost`: 54
- `saved`: 8

## Representative `both_success` Excerpts
- task 1500102 (`surface` / `both_success`)
  left: step 0 action=click('132') url=http://127.0.0.1:52800/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save error=- final=- | step 1 action=send_msg_to_user('TaskBank Amber 1450 Save and https://example.com/taskbank-1450-amber/save') url=http://127.0.0.1:52800/bookmarks error=- final=TaskBank Amber 1450 Save and https://example.com/taskbank-1450-amber/save
  right: step 0 action=click('89') url=http://127.0.0.1:32300/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save error=- final=- | step 1 action=- url=http://127.0.0.1:32300/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save&hardv3_release_ready=1 error=- final=-
- task 1500104 (`runtime` / `both_success`)
  left: step 0 action=click('132') url=http://127.0.0.1:53006/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save error=- final=- | step 1 action=send_msg_to_user('TaskBank Amber 1450 Save and https://example.com/taskbank-1450-amber/save') url=http://127.0.0.1:53006/bookmarks error=- final=TaskBank Amber 1450 Save and https://example.com/taskbank-1450-amber/save
  right: step 0 action=click('89') url=http://127.0.0.1:32506/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save error=- final=- | step 1 action=- url=http://127.0.0.1:32506/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save&hardv3_release_ready=1 error=- final=-
- task 1500105 (`process` / `both_success`)
  left: step 0 action=click('31') url=http://127.0.0.1:53005/bookmarks error=- final=- | step 1 action=send_msg_to_user('TaskBank Amber 1450 Save https://example.com/taskbank-1450-amber/save') url=http://127.0.0.1:53005/bookmarks/new error=- final=TaskBank Amber 1450 Save https://example.com/taskbank-1450-amber/save
  right: step 0 action=click('88') url=http://127.0.0.1:32505/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save error=- final=- | step 1 action=- url=http://127.0.0.1:32505/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save&hardv3_release_ready=1 error=- final=-

## Representative `lost` Excerpts
- task 1500101 (`access` / `lost`)
  left: step 0 action=click('31') url=http://127.0.0.1:52703/bookmarks error=- final=- | step 1 action=send_msg_to_user('TaskBank Amber 1450 Save https://example.com/taskbank-1450-amber/save') url=http://127.0.0.1:52703/bookmarks/new error=- final=TaskBank Amber 1450 Save https://example.com/taskbank-1450-amber/save
  right: step 0 action=- url=http://127.0.0.1:32203/bookmarks/new?url=https://example.com/taskbank-1450-amber/save&title=TaskBank+Amber+1450+Save error=- final=-
- task 1500201 (`access` / `lost`)
  left: step 0 action=click('130') url=http://127.0.0.1:52703/bookmarks/new?url=https://example.com/taskbank-1450-birch/save&title=TaskBank+Birch+1450+Save error=- final=- | step 1 action=send_msg_to_user("TaskBank Birch 1450 Save https://example.com/taskbank-1450-birch/save") url=http://127.0.0.1:52703/bookmarks error=- final=TaskBank Birch 1450 Save https://example.com/taskbank-1450-birch/save
  right: step 0 action=- url=http://127.0.0.1:32203/bookmarks/new?url=https://example.com/taskbank-1450-birch/save&title=TaskBank+Birch+1450+Save error=- final=-
- task 1500901 (`access` / `lost`)
  left: step 0 action=fill('98', 'taskbank tb1450-amber') url=http://127.0.0.1:52703/bookmarks/new?url=https://example.com/taskbank-1450-amber/filter&title=TaskBank+Amber+1450+Filter&tag_names=taskbank+tb1450-amber error=- final=- | step 1 action=- url=http://127.0.0.1:52703/bookmarks/new?url=https://example.com/taskbank-1450-amber/filter&title=TaskBank+Amber+1450+Filter&tag_names=taskbank+tb1450-amber error=- final=-
  right: step 0 action=- url=http://127.0.0.1:32203/bookmarks/new?url=https://example.com/taskbank-1450-amber/filter&title=TaskBank+Amber+1450+Filter&tag_names=taskbank+tb1450-amber error=- final=-
