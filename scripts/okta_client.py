"""
Shared Okta API helpers used by joiner.py, mover.py, and leaver.py.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

OKTA_ORG_URL = os.getenv("OKTA_ORG_URL", "").rstrip("/")
OKTA_API_TOKEN = os.getenv("OKTA_API_TOKEN", "")


def _headers() -> dict:
    return {
        "Authorization": f"SSWS {OKTA_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _raise_for_status(response: requests.Response, context: str) -> None:
    if not response.ok:
        raise RuntimeError(
            f"{context} failed [{response.status_code}]: {response.text}"
        )


def get_user(login_or_id: str) -> dict:
    """Fetch an Okta user by ID or login (email). Returns the user object."""
    url = f"{OKTA_ORG_URL}/api/v1/users/{login_or_id}"
    response = requests.get(url, headers=_headers())
    _raise_for_status(response, f"Get user '{login_or_id}'")
    user = response.json()
    print(f"Found user: {user['id']} ({user['profile']['login']})")
    return user


def find_groups_for_department(department: str) -> list[dict]:
    """Return all Okta groups whose name contains the department string."""
    url = f"{OKTA_ORG_URL}/api/v1/groups"
    params = {"q": department, "limit": 200}
    response = requests.get(url, headers=_headers(), params=params)
    _raise_for_status(response, "List groups")
    groups = response.json()
    matched = [g for g in groups if department.lower() in g["profile"]["name"].lower()]
    print(
        f"Found {len(matched)} group(s) for department '{department}': "
        f"{[g['profile']['name'] for g in matched]}"
    )
    return matched


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


def remove_user_from_groups(user_id: str, groups: list[dict]) -> None:
    """Remove the user from each group. Idempotent — 404 means already removed."""
    for group in groups:
        group_id = group["id"]
        group_name = group["profile"]["name"]
        url = f"{OKTA_ORG_URL}/api/v1/groups/{group_id}/users/{user_id}"
        response = requests.delete(url, headers=_headers())
        # 204 = removed, 404 = already not a member — both are fine
        if response.status_code not in (204, 404):
            _raise_for_status(response, f"Remove from group '{group_name}'")
        print(f"Removed from group: {group_name}")
