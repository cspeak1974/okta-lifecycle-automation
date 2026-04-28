"""
Tests for okta-lifecycle-automation
"""
from scripts.main import main


def test_main():
    assert main() is None