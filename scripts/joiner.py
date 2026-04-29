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
    OKTA_ORG_URL   — e.g. https://your-org.okta.com
    OKTA_API_TOKEN — Okta API token with User and Group write permissions
    SLACK_WEBHOOK_URL — (optional) Slack incoming webhook for welcome notification
"""

import argparse
import os
import sys

import requests
from okta_client import OKTA_ORG_URL, _headers, _raise_for_status, find_groups_for_department

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


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
# Step 2: Assign user to groups
# ---------------------------------------------------------------------------


def assign_user_to_groups(user_id: str, groups: list[dict]) -> None:
    """Add the user to each group. Idempotent — re-adding is a no-op in Okta."""
    for group in groups:
        group_id = group["id"]
        group_name = group["profile"]["name"]
        url = f"{OKTA_ORG_URL}/api/v1/groups/{group_id}/users/{user_id}"
        response = requests.put(url, headers=_headers())
        # 204 = added, 200 = already a member — both are success
        if response.status_code not in (200, 204):
            _raise_for_status(response, f"Assign group '{group_name}'")
        print(f"Assigned to group: {group_name}")


# ---------------------------------------------------------------------------
# Step 3: Activate user
# ---------------------------------------------------------------------------


def activate_user(user_id: str) -> None:
    """Activate the user and send an Okta activation email."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}/lifecycle/activate?sendEmail=true"
    response = requests.post(url, headers=_headers())
    _raise_for_status(response, "Activate user")
    print(f"Activated user: {user_id}")


# ---------------------------------------------------------------------------
# Step 4: Send Slack welcome notification (optional)
# ---------------------------------------------------------------------------


def send_slack_notification(first_name: str, last_name: str, department: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    message = {
        "text": (
            f":wave: Welcome aboard, *{first_name} {last_name}*! "
            f"They've joined the *{department}* team. "
            "Okta account created and activation email sent."
        )
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=message)
    if response.ok:
        print("Slack notification sent.")
    else:
        print(f"Slack notification failed (non-fatal): {response.status_code}")


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
    user = create_user(first_name, last_name, email, login, department)
    user_id = user["id"]

    groups = find_groups_for_department(department)
    if groups:
        assign_user_to_groups(user_id, groups)
    else:
        print(
            f"Warning: no groups found for department '{department}' — skipping group assignment."
        )

    activate_user(user_id)
    send_slack_notification(first_name, last_name, department)

    print(f"\nJoiner complete for {first_name} {last_name} ({email}).")
    return user


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
