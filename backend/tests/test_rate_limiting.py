"""
Tests for rate limiting functionality.
"""
import pytest
from flask import Flask
from app import create_app
from utils.rate_limiter import limiter


@pytest.fixture
def app():
    """Create test Flask app."""
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_rate_limiter_initialized(app):
    """Test that rate limiter is initialized."""
    assert limiter is not None
    assert hasattr(app, 'extensions')
    assert 'limiter' in app.extensions


def test_rate_limit_on_analyze_endpoint(client):
    """Test rate limiting on analyze endpoint."""
    # Make multiple requests quickly
    for i in range(6):  # Should hit limit at 5
        response = client.post('/api/analyze', json={
            'location': 'Bogotá',
            'theme': 'Seguridad'
        })
        
        if i < 5:
            # First 5 should work (or fail for other reasons, but not rate limit)
            assert response.status_code != 429
        else:
            # 6th should be rate limited
            assert response.status_code == 429


def test_rate_limit_on_chat_endpoint(client):
    """Test rate limiting on chat endpoint."""
    # Make multiple requests quickly
    for i in range(11):  # Should hit limit at 10
        response = client.post('/api/chat', json={
            'message': 'Test message'
        })
        
        if i < 10:
            assert response.status_code != 429
        else:
            assert response.status_code == 429

