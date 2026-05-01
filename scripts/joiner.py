"""
joiner.py — provision a new Okta user, assign department groups, and activate.

Usage:
    python scripts/joiner.py \
        --first-name Jane \
        --last-name Doe \
        --email jane.doe@example.com \
        --login jane.doe@example.com \
        --department Engineering

Environment variables required (.env):
    OKTA_ORG_URL         — e.g. https://your-org.okta.com
    OKTA_API_TOKEN       — Okta API token with User and Group write permissions
    SLACK_WEBHOOK_EVENTS — (optional) Slack incoming webhook for #okta-events channel
    SLACK_WEBHOOK_ERRORS — (optional) Slack incoming webhook for #okta-errors channel
"""

import argparse
import os
import sys

# Add project root to sys.path so utils/ is importable when running scripts directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from okta_client import (
    OKTA_ORG_URL,
    _headers,
    _raise_for_status,
    assign_user_to_groups,
    find_groups_for_department,
)

from utils.slack import notify_error, notify_event

# ---------------------------------------------------------------------------
# Step 1: Create user
# ---------------------------------------------------------------------------


def create_user(
    first_name: str,
    last_name: str,
    email: str,
    login: str,
    department: str,
) -> dict:
    """Create a staged (not yet active) Okta user and return the user object."""
    url = f"{OKTA_ORG_URL}/api/v1/users?activate=false"
    payload = {
        "profile": {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "login": login,
            "department": department,
        }
    }
    response = requests.post(url, headers=_headers(), json=payload)
    _raise_for_status(response, "Create user")
    user = response.json()
    print(f"Created user: {user['id']} ({login})")
    return user


# ---------------------------------------------------------------------------
# Step 2: Activate user
# ---------------------------------------------------------------------------


def activate_user(user_id: str) -> None:
    """Activate the user and send an Okta activation email."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}/lifecycle/activate?sendEmail=true"
    response = requests.post(url, headers=_headers())
    _raise_for_status(response, "Activate user")
    print(f"Activated user: {user_id}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def provision_user(
    first_name: str,
    last_name: str,
    email: str,
    login: str,
    department: str,
) -> dict:
    """Full joiner flow. Returns the created user object."""
    try:
        user = create_user(first_name, last_name, email, login, department)
        user_id = user["id"]

        groups = find_groups_for_department(department)
        if groups:
            assign_user_to_groups(user_id, groups)
        else:
            print(
                f"Warning: no groups found for department '{department}'"
                " — skipping group assignment."
            )

        activate_user(user_id)

        print(f"\nJoiner complete for {first_name} {last_name} ({email}).")
        notify_event(
            f":white_check_mark: Joiner complete: *{login}* ({user_id}) provisioned and activated."
        )
        return user
    except Exception as exc:
        notify_error(f":x: Joiner failed for *{login}*: {exc}")
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision a new Okta user (joiner).")
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--login", help="Okta login (defaults to --email)")
    parser.add_argument("--department", required=True)
    return parser.parse_args()


def _validate_env() -> None:
    missing = [var for var in ("OKTA_ORG_URL", "OKTA_API_TOKEN") if not os.getenv(var)]
    if missing:
        print(
            f"Error: missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    _validate_env()
    args = _parse_args()
    provision_user(
        first_name=args.first_name,
        last_name=args.last_name,
        email=args.email,
        login=args.login or args.email,
        department=args.department,
    )
