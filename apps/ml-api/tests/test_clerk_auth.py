"""Clerk JWKS verification is covered by integration tests with real keys.

Unit tests here are optional; `app/core/clerk.py` raises on malformed tokens.
"""

import pytest


@pytest.mark.skip(reason="Requires HEARTSCAN_CLERK_JWKS_URL and a signed Clerk JWT")
def test_verify_clerk_placeholder() -> None:
    assert True
