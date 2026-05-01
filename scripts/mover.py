"""
mover.py — update an Okta user's department: swap group memberships and update their profile.

Usage:
    # by Okta user ID
    python scripts/mover.py --user-id 00u1ab2cd3EF4GH5IJ6 --new-department Marketing

    # by login (email) — the script will look up the user ID first
    python scripts/mover.py --login jane.doe@example.com --new-department Marketing

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
    get_user,
    remove_user_from_groups,
)

from utils.slack import notify_error, notify_event

# ---------------------------------------------------------------------------
# Step 3: Update department attribute on Okta profile
# ---------------------------------------------------------------------------


def update_user_department(user_id: str, new_department: str) -> None:
    """Update the department field on the user's Okta profile."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{user_id}"
    payload = {"profile": {"department": new_department}}
    response = requests.post(url, headers=_headers(), json=payload)
    _raise_for_status(response, "Update user profile")
    print(f"Updated profile department to '{new_department}' for user: {user_id}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def move_user(login_or_id: str, new_department: str) -> dict:
    """Full mover flow. Returns the updated user object."""
    try:
        user = get_user(login_or_id)
        user_id = user["id"]
        login = user["profile"]["login"]
        old_department = user["profile"].get("department", "")

        if old_department:
            old_groups = find_groups_for_department(old_department)
            if old_groups:
                remove_user_from_groups(user_id, old_groups)
            else:
                print(f"No groups found for old department '{old_department}' — skipping removal.")
        else:
            print("No existing department on profile — skipping old group removal.")

        new_groups = find_groups_for_department(new_department)
        if new_groups:
            assign_user_to_groups(user_id, new_groups)
        else:
            print(
                f"Warning: no groups found for new department '{new_department}'"
                " — skipping group assignment."
            )

        update_user_department(user_id, new_department)

        print(f"\nMover complete for {login}: '{old_department}' → '{new_department}'.")
        notify_event(
            f":arrows_counterclockwise: Mover complete: *{login}* ({user_id}) moved "
            f"from *{old_department or '(none)'}* to *{new_department}*."
        )
        return user
    except Exception as exc:
        notify_error(f":x: Mover failed for *{login_or_id}*: {exc}")
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move an Okta user to a new department.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", help="Okta user ID (e.g. 00u1ab2cd3EF4GH5IJ6)")
    group.add_argument("--login", help="Okta login / email address")
    parser.add_argument("--new-department", required=True, help="Target department name")
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
    move_user(args.user_id or args.login, args.new_department)
