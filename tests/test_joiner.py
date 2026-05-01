"""Tests for scripts/joiner.py — all HTTP calls are mocked."""

from unittest.mock import MagicMock, patch

import pytest

import scripts.joiner as joiner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_data=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


FAKE_USER = {
    "id": "00u1ab2cd3EF4GH5IJ6",
    "profile": {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
        "login": "jane.doe@example.com",
        "department": "Engineering",
    },
}

FAKE_GROUPS = [
    {"id": "00g1eng0000ABC", "profile": {"name": "Engineering"}},
    {"id": "00g1eng0000XYZ", "profile": {"name": "Engineering-Leads"}},
    {"id": "00g1mkt0000DEF", "profile": {"name": "Marketing"}},  # should not match
]


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_happy_path(self):
        with patch("scripts.joiner.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200, FAKE_USER)

            user = joiner.create_user(
                first_name="Jane",
                last_name="Doe",
                email="jane.doe@example.com",
                login="jane.doe@example.com",
                department="Engineering",
            )

        assert user["id"] == FAKE_USER["id"]
        mock_post.assert_called_once()
        url_used = mock_post.call_args[0][0]
        assert "activate=false" in url_used

    def test_400_raises_runtime_error(self):
        error_body = '{"errorCode":"E0000001","errorSummary":"Api validation failed"}'
        with patch("scripts.joiner.requests.post") as mock_post:
            mock_post.return_value = _mock_response(400, text=error_body)

            with pytest.raises(RuntimeError, match="Create user failed \\[400\\]"):
                joiner.create_user(
                    first_name="Jane",
                    last_name="Doe",
                    email="jane.doe@example.com",
                    login="jane.doe@example.com",
                    department="Engineering",
                )


# ---------------------------------------------------------------------------
# find_groups_for_department
# ---------------------------------------------------------------------------

class TestFindGroupsForDepartment:
    def test_returns_only_matching_groups(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, FAKE_GROUPS)

            matched = joiner.find_groups_for_department("Engineering")

        assert len(matched) == 2
        names = [g["profile"]["name"] for g in matched]
        assert "Engineering" in names
        assert "Engineering-Leads" in names
        assert "Marketing" not in names

    def test_no_matches_returns_empty_list(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, FAKE_GROUPS)

            matched = joiner.find_groups_for_department("Finance")

        assert matched == []

    def test_api_error_raises(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(403, text="Forbidden")

            with pytest.raises(RuntimeError, match="List groups failed \\[403\\]"):
                joiner.find_groups_for_department("Engineering")


# ---------------------------------------------------------------------------
# assign_user_to_groups
# ---------------------------------------------------------------------------

class TestAssignUserToGroups:
    def test_puts_to_each_group(self):
        groups = FAKE_GROUPS[:2]  # Engineering, Engineering-Leads
        with patch("okta_client.requests.put") as mock_put:
            mock_put.return_value = _mock_response(204)

            joiner.assign_user_to_groups("00u1ab2cd3EF4GH5IJ6", groups)

        assert mock_put.call_count == 2

    def test_200_already_member_is_ok(self):
        groups = [FAKE_GROUPS[0]]
        with patch("okta_client.requests.put") as mock_put:
            mock_put.return_value = _mock_response(200)  # already a member

            joiner.assign_user_to_groups("00u1ab2cd3EF4GH5IJ6", groups)

        mock_put.assert_called_once()

    def test_non_200_204_raises(self):
        groups = [FAKE_GROUPS[0]]
        with patch("okta_client.requests.put") as mock_put:
            mock_put.return_value = _mock_response(500, text="Internal Server Error")

            with pytest.raises(RuntimeError, match="Assign group 'Engineering' failed \\[500\\]"):
                joiner.assign_user_to_groups("00u1ab2cd3EF4GH5IJ6", groups)


# ---------------------------------------------------------------------------
# activate_user
# ---------------------------------------------------------------------------

class TestActivateUser:
    def test_happy_path(self):
        with patch("scripts.joiner.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200)

            joiner.activate_user("00u1ab2cd3EF4GH5IJ6")

        mock_post.assert_called_once()
        url_used = mock_post.call_args[0][0]
        assert "lifecycle/activate" in url_used

    def test_error_raises(self):
        with patch("scripts.joiner.requests.post") as mock_post:
            mock_post.return_value = _mock_response(409, text="User already active")

            with pytest.raises(RuntimeError, match="Activate user failed \\[409\\]"):
                joiner.activate_user("00u1ab2cd3EF4GH5IJ6")


# ---------------------------------------------------------------------------
# provision_user (orchestrator)
# ---------------------------------------------------------------------------

class TestProvisionUser:
    def test_happy_path_calls_all_steps(self):
        with (
            patch("scripts.joiner.create_user", return_value=FAKE_USER) as mock_create,
            patch(
                "scripts.joiner.find_groups_for_department", return_value=FAKE_GROUPS[:2]
            ) as mock_groups,
            patch("scripts.joiner.assign_user_to_groups") as mock_assign,
            patch("scripts.joiner.activate_user") as mock_activate,
            patch("scripts.joiner.notify_event") as mock_notify_event,
            patch("scripts.joiner.notify_error") as mock_notify_error,
        ):
            result = joiner.provision_user(
                first_name="Jane",
                last_name="Doe",
                email="jane.doe@example.com",
                login="jane.doe@example.com",
                department="Engineering",
            )

        assert result == FAKE_USER
        mock_create.assert_called_once_with(
            "Jane", "Doe", "jane.doe@example.com", "jane.doe@example.com", "Engineering"
        )
        mock_groups.assert_called_once_with("Engineering")
        mock_assign.assert_called_once_with(FAKE_USER["id"], FAKE_GROUPS[:2])
        mock_activate.assert_called_once_with(FAKE_USER["id"])
        mock_notify_event.assert_called_once()
        mock_notify_error.assert_not_called()

    def test_skips_group_assignment_when_no_groups_found(self):
        with (
            patch("scripts.joiner.create_user", return_value=FAKE_USER),
            patch("scripts.joiner.find_groups_for_department", return_value=[]),
            patch("scripts.joiner.assign_user_to_groups") as mock_assign,
            patch("scripts.joiner.activate_user"),
            patch("scripts.joiner.notify_event"),
            patch("scripts.joiner.notify_error"),
        ):
            joiner.provision_user(
                first_name="Jane",
                last_name="Doe",
                email="jane.doe@example.com",
                login="jane.doe@example.com",
                department="Finance",
            )

        mock_assign.assert_not_called()

    def test_error_calls_notify_error_and_reraises(self):
        with (
            patch(
                "scripts.joiner.create_user", side_effect=RuntimeError("API error")
            ),
            patch("scripts.joiner.notify_event") as mock_notify_event,
            patch("scripts.joiner.notify_error") as mock_notify_error,
        ):
            with pytest.raises(RuntimeError, match="API error"):
                joiner.provision_user(
                    first_name="Jane",
                    last_name="Doe",
                    email="jane.doe@example.com",
                    login="jane.doe@example.com",
                    department="Engineering",
                )

        mock_notify_error.assert_called_once()
        mock_notify_event.assert_not_called()
