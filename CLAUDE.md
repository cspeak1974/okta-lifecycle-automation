# CLAUDE.md — okta-lifecycle-automation

This file provides context for Claude Code about this project.

## What We're Building

A complete **joiner/mover/leaver identity lifecycle automation kit** using:
- **Okta API** (Python scripts) — for programmatic user provisioning and deprovisioning
- **Okta Workflows** (low-code) — for event-driven automation and orchestration

## Okta Environment

- **Plan:** Integrator Free Plan
- **Org URL:** stored in .env as OKTA_ORG_URL
- **Auth:** API token stored in .env as OKTA_API_TOKEN
- **Limits:** 10 active users, 5 Workflows flows

## Project Structure

```
okta-lifecycle-automation/
├── scripts/
│   ├── joiner.py       ← provision new user, assign groups, activate
│   ├── mover.py        ← update groups/profile on role/department change
│   └── leaver.py       ← suspend, remove groups, revoke sessions, deactivate
├── tests/
│   ├── test_joiner.py
│   ├── test_mover.py
│   └── test_leaver.py
├── docs/
│   └── architecture.md ← design decisions and system overview
├── workflows/
│   ├── joiner-flow.png
│   ├── mover-flow.png
│   ├── leaver-flow.png
│   ├── slack-notification.png
│   └── error-logger.png
├── .vscode/
│   └── settings.json
├── .env                ← never commit this
├── .env.example        ← template for required env vars
├── .gitignore
├── Makefile
├── README.md
└── requirements.txt
```

## Okta Workflows Plan (5 flow limit)

1. **Joiner trigger flow** — fires on "User Created" event
2. **Leaver trigger flow** — fires on "User Deactivated" event
3. **Mover trigger flow** — fires on profile attribute change (department)
4. **Slack notification helper** — called by the above, sends Slack message
5. **Error/audit logger** — writes to Google Sheet or sends alert on failure

## Python Scripts Plan

### joiner.py
- Create user via Okta API
- Assign to groups based on department
- Activate user
- Trigger welcome notification

### mover.py
- Accept user ID and new department
- Remove from old department groups
- Add to new department groups
- Update profile attributes

### leaver.py
- Suspend user
- Revoke all active sessions
- Remove from all groups
- Deactivate user

## Environment Variables

```
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-api-token-here
SLACK_WEBHOOK_URL=your-slack-webhook-url (optional)
```

## Key Design Decisions

- Scripts use the Okta REST API directly via `requests` rather than the Okta Python SDK
  to demonstrate API fluency and keep dependencies minimal
- Each script is standalone and can be run independently or triggered by Okta Workflows
- Group assignments are department-based — department name maps to Okta group names
- All scripts are idempotent — safe to run multiple times without side effects
- `.env` file used for local development credentials — never committed to git.
  In production, secrets would be managed via a dedicated secret manager such as
  HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault, with environment
  variables injected at runtime by the deployment platform (Kubernetes, Docker, CI/CD)
  
## VS Code Settings Notes

- `python.defaultInterpreterPath` — explicitly points to `.venv` to fix interpreter detection
- `python.analysis.extraPaths` — adds `scripts/` to Pylance's analysis path, fixing
  "module not found" warnings when importing from `okta_client`
- `python.terminal.useEnvFile` — injects `.env` variables into the integrated terminal

## Testing Guidelines

- Write tests for every new script or function
- Use `pytest` as the test framework
- Mock all external API calls using `unittest.mock.patch` — never make real API calls in tests
- Always cover the happy path for every function
- Cover at least one error/sad path per function (e.g. API returns 4xx, missing env vars)
- Test files live in `tests/` and mirror the script name (e.g. `scripts/joiner.py` → `tests/test_joiner.py`)
- Run tests with `make test`

## What's Done

- [x] Okta Integrator Free Plan set up
- [x] API token created
- [x] Project scaffolded with Cookiecutter template
- [x] GitHub repo created
- [x] `.env` configured with Okta credentials
- [x] Dependencies installed (requests, python-dotenv, pytest, ruff)
- [x] `pyproject.toml` configured with pytest and ruff settings
- [x] `joiner.py` written and tested against live Okta org
- [x] `tests/test_joiner.py` written with mocked API calls
- [x] `make lint` and `make test` both passing
- [x] Engineering and IT groups created in Okta for testing
- [x] Write `leaver.py` — suspend, revoke sessions, remove groups, deactivate
- [x] Write `tests/test_leaver.py`
- [x] Write `mover.py` — update groups/profile on department change
- [x] Write `tests/test_mover.py`

## What's Next

- [ ] Build Okta Workflows (5 flows)
- [ ] Screenshot and document Workflows in `workflows/`
- [ ] Write `docs/architecture.md`
- [ ] Polish README for hiring manager
- [ ] Set up branch protection on main
- [ ] Demo dry run

## Optional / Stretch Goals

- [ ] Replace hardcoded group IDs in joiner flow with dynamic lookup
        (e.g. store department → group ID mapping as Okta custom attribute
        or Workflows table, look up at runtime instead of hardcoding)
- [ ] Add If/Else branch to joiner flow to assign group based on
        department attribute (Engineering vs IT) instead of hardcoding
        a single group for all new users
