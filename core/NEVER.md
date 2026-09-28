# NEVER.md - forbidden patterns (all platforms, all tasks)

| Forbidden | Why | Alternative |
|-----------|-----|-------------|
| shell write text files | unsafe, no diff preview | use Write/Edit tool |
| empty catch | hides bugs | handle or re-raise |
| controller writes business | wrong layer | business in service |
| loop SQL (N+1) | performance | join / batch |
| silent data loss | corrupt state | raise on parse fail |
| cache update before commit | race | update after commit |
| auto git push | destructive | explicit user push |
| implementer = reviewer | blind spot | separate Agent instance |
| edit unread file | guessing | read first |
| over-abstract on first use | complexity | wait for 2nd occurrence |
| multi-line if without braces | bug-prone | always brace |
| "大概"/"差不多" in code | slop | exact match or fail |
