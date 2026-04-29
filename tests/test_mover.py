"""Tests for scripts/mover.py — all HTTP calls are mocked."""

from unittest.mock import MagicMock, patch

import pytest

import scripts.mover as mover

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

FAKE_USER_NO_DEPT = {
    "id": "00u1ab2cd3EF4GH5IJ6",
    "profile": {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
        "login": "jane.doe@example.com",
        "department": "",
    },
}

ENG_GROUPS = [
    {"id": "00g1eng0000ABC", "profile": {"name": "Engineering"}},
    {"id": "00g1eng0000XYZ", "profile": {"name": "Engineering-Leads"}},
]

MKT_GROUPS = [
    {"id": "00g1mkt0000DEF", "profile": {"name": "Marketing"}},
]


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    def test_happy_path(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, FAKE_USER)

            user = mover.get_user("jane.doe@example.com")

        assert user["id"] == FAKE_USER["id"]

    def test_404_raises(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(404, text="Not found")

            with pytest.raises(RuntimeError, match="Get user .* failed \\[404\\]"):
                mover.get_user("nobody@example.com")


# ---------------------------------------------------------------------------
# find_groups_for_department
# ---------------------------------------------------------------------------


class TestFindGroupsForDepartment:
    def test_returns_matching_groups(self):
        all_groups = ENG_GROUPS + MKT_GROUPS
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, all_groups)

            matched = mover.find_groups_for_department("Engineering")

        assert len(matched) == 2
        assert all("Engineering" in g["profile"]["name"] for g in matched)

    def test_no_matches_returns_empty_list(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(200, ENG_GROUPS)

            matched = mover.find_groups_for_department("Finance")

        assert matched == []

    def test_api_error_raises(self):
        with patch("okta_client.requests.get") as mock_get:
            mock_get.return_value = _mock_response(403, text="Forbidden")

            with pytest.raises(RuntimeError, match="List groups failed \\[403\\]"):
                mover.find_groups_for_department("Engineering")


# ---------------------------------------------------------------------------
# remove_user_from_groups
# ---------------------------------------------------------------------------


class TestRemoveUserFromGroups:
    def test_deletes_from_each_group(self):
        with patch("okta_client.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(204)

            mover.remove_user_from_groups("00u1ab2cd3EF4GH5IJ6", ENG_GROUPS)

        assert mock_delete.call_count == 2

    def test_404_already_removed_is_ok(self):
        with patch("okta_client.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(404)

            mover.remove_user_from_groups("00u1ab2cd3EF4GH5IJ6", ENG_GROUPS)

    def test_500_raises(self):
        with patch("okta_client.requests.delete") as mock_delete:
            mock_delete.return_value = _mock_response(500, text="Server error")

            with pytest.raises(
                RuntimeError, match="Remove from group 'Engineering' failed \\[500\\]"
            ):
                mover.remove_user_from_groups("00u1ab2cd3EF4GH5IJ6", ENG_GROUPS)


# ---------------------------------------------------------------------------
# assign_user_to_groups
# ---------------------------------------------------------------------------


class TestAssignUserToGroups:
    def test_puts_to_each_group(self):
        with patch("okta_client.requests.put") as mock_put:
            mock_put.return_value = _mock_response(204)

            mover.assign_user_to_groups("00u1ab2cd3EF4GH5IJ6", MKT_GROUPS)

        assert mock_put.call_count == 1

    def test_200_already_member_is_ok(self):
        with patch("okta_client.requests.put") as mock_put:
            mock_put.return_value = _mock_response(200)

            mover.assign_user_to_groups("00u1ab2cd3EF4GH5IJ6", MKT_GROUPS)

        mock_put.assert_called_once()

    def test_error_raises(self):
        with patch("okta_client.requests.put") as mock_put:
            mock_put.return_value = _mock_response(500, text="Server error")

            with pytest.raises(
                RuntimeError, match="Assign group 'Marketing' failed \\[500\\]"
            ):
                mover.assign_user_to_groups("00u1ab2cd3EF4GH5IJ6", MKT_GROUPS)


# ---------------------------------------------------------------------------
# update_user_department
# ---------------------------------------------------------------------------


class TestUpdateUserDepartment:
    def test_happy_path(self):
        with patch("scripts.mover.requests.post") as mock_post:
            mock_post.return_value = _mock_response(200, FAKE_USER)

            mover.update_user_department("00u1ab2cd3EF4GH5IJ6", "Marketing")

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert payload["profile"]["department"] == "Marketing"

    def test_error_raises(self):
        with patch("scripts.mover.requests.post") as mock_post:
            mock_post.return_value = _mock_response(400, text="Validation error")

            with pytest.raises(RuntimeError, match="Update user profile failed \\[400\\]"):
                mover.update_user_department("00u1ab2cd3EF4GH5IJ6", "Marketing")


# ---------------------------------------------------------------------------
# send_slack_notification
# ---------------------------------------------------------------------------


class TestSendSlackNotification:
    def test_skips_when_no_webhook_url(self):
        with patch.object(mover, "SLACK_WEBHOOK_URL", ""):
            with patch("scripts.mover.requests.post") as mock_post:
                mover.send_slack_notification("jane.doe@example.com", "Engineering", "Marketing")

        mock_post.assert_not_called()

    def test_posts_with_correct_content(self):
        with patch.object(mover, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/fake"):
            with patch("scripts.mover.requests.post") as mock_post:
                mock_post.return_value = _mock_response(200)

                mover.send_slack_notification("jane.doe@example.com", "Engineering", "Marketing")

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert "jane.doe@example.com" in payload["text"]
        assert "Engineering" in payload["text"]
        assert "Marketing" in payload["text"]

    def test_failed_webhook_does_not_raise(self):
        with patch.object(mover, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/fake"):
            with patch("scripts.mover.requests.post") as mock_post:
                mock_post.return_value = _mock_response(500)

                mover.send_slack_notification("jane.doe@example.com", "Engineering", "Marketing")


# ---------------------------------------------------------------------------
# move_user (orchestrator)
# ---------------------------------------------------------------------------


class TestMoveUser:
    def test_happy_path_calls_all_steps(self):
        with (
            patch("scripts.mover.get_user", return_value=FAKE_USER) as mock_get_user,
            patch(
                "scripts.mover.find_groups_for_department", side_effect=[ENG_GROUPS, MKT_GROUPS]
            ) as mock_find,
            patch("scripts.mover.remove_user_from_groups") as mock_remove,
            patch("scripts.mover.assign_user_to_groups") as mock_assign,
            patch("scripts.mover.update_user_department") as mock_update,
            patch("scripts.mover.send_slack_notification") as mock_slack,
        ):
            result = mover.move_user("jane.doe@example.com", "Marketing")

        assert result == FAKE_USER
        mock_get_user.assert_called_once_with("jane.doe@example.com")
        assert mock_find.call_count == 2
        mock_find.assert_any_call("Engineering")
        mock_find.assert_any_call("Marketing")
        mock_remove.assert_called_once_with(FAKE_USER["id"], ENG_GROUPS)
        mock_assign.assert_called_once_with(FAKE_USER["id"], MKT_GROUPS)
        mock_update.assert_called_once_with(FAKE_USER["id"], "Marketing")
        mock_slack.assert_called_once_with(
            FAKE_USER["profile"]["login"], "Engineering", "Marketing"
        )

    def test_skips_old_group_removal_when_no_department_on_profile(self):
        with (
            patch("scripts.mover.get_user", return_value=FAKE_USER_NO_DEPT),
            patch("scripts.mover.find_groups_for_department", return_value=MKT_GROUPS),
            patch("scripts.mover.remove_user_from_groups") as mock_remove,
            patch("scripts.mover.assign_user_to_groups"),
            patch("scripts.mover.update_user_department"),
            patch("scripts.mover.send_slack_notification"),
        ):
            mover.move_user("jane.doe@example.com", "Marketing")

        mock_remove.assert_not_called()

    def test_skips_old_group_removal_when_no_old_groups_found(self):
        with (
            patch("scripts.mover.get_user", return_value=FAKE_USER),
            patch(
                "scripts.mover.find_groups_for_department", side_effect=[[], MKT_GROUPS]
            ),
            patch("scripts.mover.remove_user_from_groups") as mock_remove,
            patch("scripts.mover.assign_user_to_groups"),
            patch("scripts.mover.update_user_department"),
            patch("scripts.mover.send_slack_notification"),
        ):
            mover.move_user("jane.doe@example.com", "Marketing")

        mock_remove.assert_not_called()

    def test_skips_new_group_assignment_when_no_new_groups_found(self):
        with (
            patch("scripts.mover.get_user", return_value=FAKE_USER),
            patch(
                "scripts.mover.find_groups_for_department", side_effect=[ENG_GROUPS, []]
            ),
            patch("scripts.mover.remove_user_from_groups"),
            patch("scripts.mover.assign_user_to_groups") as mock_assign,
            patch("scripts.mover.update_user_department"),
            patch("scripts.mover.send_slack_notification"),
        ):
            mover.move_user("jane.doe@example.com", "Finance")

        mock_assign.assert_not_called()
