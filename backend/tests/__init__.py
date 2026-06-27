"""
Unit tests for the main conftest.py at the tests package level.
Re-exports fixtures from tests/fixtures/conftest.py.
"""
# Make fixtures available throughout the tests package
from backend.tests.fixtures.conftest import (  # noqa: F401
    event_loop,
    mock_db_session,
    mock_redis,
    minimal_app,
    client,
)
