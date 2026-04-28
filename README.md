# okta-lifecycle-automation

A Python-based identity lifecycle automation kit for Okta. Automates the full
joiner/mover/leaver lifecycle using the Okta REST API and Okta Workflows.

## Overview

Managing user identity manually is error-prone and slow. This project automates
the three core lifecycle events:

- **Joiner** — provision a new user, assign to groups based on department, activate
- **Mover** — update group memberships and profile when a user changes roles
- **Leaver** — suspend, revoke sessions, remove from groups, deactivate

## Prerequisites

- Python 3.13+
- An Okta org (free [Integrator Free Plan](https://developer.okta.com/signup/) works)
- An Okta API token

## Setup

Clone the repo:

```bash
git clone https://github.com/cspeak1974/okta-lifecycle-automation.git
cd okta-lifecycle-automation
```

Install dependencies:

```bash
make install
```

This creates a `.venv` virtual environment and installs all dependencies including
`requests` and `python-dotenv`. Reopen your terminal after running to activate the
virtual environment.

Copy `.env.example` to `.env` and add your Okta credentials:

```bash
cp .env.example .env
```

```
OKTA_ORG_URL=https://your-okta-org.okta.com
OKTA_API_TOKEN=your-api-token-here
SLACK_WEBHOOK_URL=your-slack-webhook-url (optional)
```

## Usage

```bash
make run
```

## Development

```bash
make test      # run tests
make lint      # run ruff linter
make format    # run ruff formatter
make clean     # remove build artifacts
```

## Testing

Tests use `pytest` with mocked API calls — no real Okta credentials needed to run tests.

```bash
make test
```

## Project Structure

```
├── scripts/
│   ├── joiner.py       ← provision new user, assign groups, activate
│   ├── mover.py        ← update groups/profile on role/department change
│   └── leaver.py       ← suspend, remove groups, revoke sessions, deactivate
├── tests/              ← pytest tests
├── docs/
│   └── architecture.md ← design decisions and system overview
├── workflows/          ← Okta Workflows screenshots and documentation
├── .env.example        ← environment variable template
├── Makefile
└── requirements.txt
```

## Author

Clayton Speak <clayton@claytonspeak.com>