# Architecture — okta-lifecycle-automation

## Overview

This project automates the three core identity lifecycle events in Okta:

- **Joiner** — provision a new user, assign to department groups, activate
- **Mover** — update group memberships and profile when a user changes departments
- **Leaver** — suspend, revoke sessions, remove from groups, deactivate

Each lifecycle event is implemented as a standalone Python script that can be
run independently from the CLI or triggered by an external system such as
Okta Workflows, an HR platform webhook, or a CI/CD pipeline.

---

## Architecture Diagram

```
HR System / Manual Trigger
        │
        ▼
  CLI / Okta Workflows
        │
        ├──▶ joiner.py ──▶ Create User ──▶ Assign Groups ──▶ Activate
        │
        ├──▶ mover.py  ──▶ Get User ──▶ Remove Old Groups ──▶ Add New Groups ──▶ Update Profile
        │
        └──▶ leaver.py ──▶ Get User ──▶ Suspend ──▶ Revoke Sessions ──▶ Remove Groups ──▶ Deactivate
                │
                └──▶ okta_client.py (shared helpers)
                        │
                        └──▶ Okta REST API
```

---

## Components

### `utils/slack.py`
Shared Slack notification helpers used by all three lifecycle scripts:
- `notify_event(message)` — posts to the `#okta-events` channel via `SLACK_WEBHOOK_EVENTS`
- `notify_error(message)` — posts to the `#okta-errors` channel via `SLACK_WEBHOOK_ERRORS`

Both functions are non-fatal: if the webhook URL is not configured or the request fails, a
warning is printed and execution continues. Each lifecycle orchestrator calls `notify_event`
on successful completion and `notify_error` in its except block before re-raising.

### `scripts/okta_client.py`
Shared module containing common helpers used across all three scripts:
- `_headers()` — builds Okta API auth headers
- `_raise_for_status()` — consistent error handling for API responses
- `get_user()` — fetch a user by ID or login (email)
- `find_groups_for_department()` — find Okta groups matching a department name

### `scripts/joiner.py`
Provisions a new Okta user. Steps:
1. Create user in staged state (not yet active)
2. Find groups matching the user's department
3. Assign user to matching groups
4. Activate user (sends activation email in production)
5. Send optional Slack welcome notification

### `scripts/mover.py`
Moves a user to a new department. Steps:
1. Look up user by ID or login
2. Find and remove groups matching old department
3. Find and assign groups matching new department
4. Update department attribute on Okta profile
5. Send optional Slack move notification

### `scripts/leaver.py`
Offboards a user. Steps:
1. Look up user by ID or login
2. Suspend user
3. Revoke all active sessions
4. Remove from all non-system groups
5. Deactivate user
6. Send optional Slack offboarding notification

---

## Design Decisions

### Raw `requests` over Okta Python SDK
Scripts use the `requests` library to call the Okta REST API directly rather
than using the official `okta-sdk-python` SDK. This was a deliberate choice to
demonstrate REST API fluency. In production, the SDK would be preferred as it
handles auth, retries, pagination, and rate limiting automatically.

### `sendEmail=false` on activation and deactivation
Activation and deactivation calls use `sendEmail=false` during development to
avoid sending real emails to test addresses. This should be set to `true` in
production so users receive Okta's activation and offboarding emails.

### `.env` for local credentials
Credentials are stored in a `.env` file for local development, which is the
standard approach. In production, secrets should be managed via a dedicated
secret manager such as HashiCorp Vault, AWS Secrets Manager, or Azure Key
Vault, with environment variables injected at runtime by the deployment
platform (Kubernetes, Docker, CI/CD).

### Functional/procedural style
Scripts use a functional/procedural style rather than OOP. This keeps the code
simple and readable for a scripting and automation context. A production
implementation would benefit from an `OktaClient` class with session reuse,
connection pooling, and easier mocking in tests.

### Idempotent operations
All scripts are designed to be idempotent — safe to run multiple times without
unintended side effects. For example:
- Re-adding a user to a group they're already in is a no-op
- Suspending an already-suspended user is handled gracefully
- Removing a user from a group they're not in (404) is treated as success

---

## Known Limitations and Future Improvements

### No retry logic
If Okta rate-limits or returns a transient error the script fails immediately.
Production code should implement exponential backoff with jitter, ideally using
a library like `tenacity`.

### No pagination
Group and user list endpoints use `limit: 200` which works for small orgs but
would miss results in larger ones. Production code should follow Okta's
pagination links in the `Link` response header.

### Fuzzy group matching
`find_groups_for_department()` uses a substring match which could match
unintended groups (e.g. searching "Eng" could match both "Engineering" and
"Eng-Contractors"). A more robust approach would use exact name matching or
maintain an explicit department-to-group-ID mapping.

### Fragile "already suspended" check
`leaver.py` checks for the string "already suspended" in the error response
body, which relies on Okta's error message wording not changing. A more robust
approach would check against Okta's error code `E0000001`.

### No structured logging
Scripts use `print()` for output. Production code should use Python's `logging`
module with structured log output (e.g. JSON) for better observability and
integration with SIEM tools.

### No HR system integration
Currently scripts are triggered manually via CLI. A production implementation
would integrate with an HR platform (e.g. Workday, BambooHR) via webhooks or
API polling to trigger lifecycle events automatically when employee records
change.

### Slack notifications use incoming webhooks
`utils/slack.py` posts notifications via Slack incoming webhook URLs. This is
simple to set up but lacks retry logic, rate-limit handling, and rich message
formatting. A production implementation would use the Slack SDK (`slack_sdk`)
with proper error handling, exponential backoff, and Block Kit messages for
richer formatting.