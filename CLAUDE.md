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

## What's Done

- [x] Okta Integrator Free Plan set up
- [x] API token created
- [x] Project scaffolded with Cookiecutter template
- [x] GitHub repo created

## What's Next

- [ ] Set up .env with Okta credentials
- [ ] Install dependencies (okta, requests, python-dotenv)
- [ ] Write joiner.py
- [ ] Write mover.py
- [ ] Write leaver.py
- [ ] Write tests
- [ ] Build Okta Workflows
- [ ] Screenshot and document Workflows
- [ ] Write architecture.md
- [ ] Polish README for hiring manager
- [ ] Set up branch protection on main
- [ ] Demo dry run