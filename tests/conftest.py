"""
ShadowMap Enterprise - Test Fixtures

Global pytest fixtures for test suite.
"""

import pytest


@pytest.fixture
def sample_confidence_data():
    """Sample data for confidence calculation tests."""
    return {
        "high_trust_source": "reuters.com",
        "low_trust_source": "telegram",
        "high_trust_method": "gpt-4o",
        "low_trust_method": "regex_extraction",
    }
