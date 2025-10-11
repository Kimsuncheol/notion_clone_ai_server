"""
Shared pytest configuration and fixtures for recommendation tests.
This file connects the test modules and provides shared setup.
"""
import pytest
from fastapi.testclient import TestClient
from main import app, NOTES, USERS, notes_index


@pytest.fixture(scope="function")
def clean_state():
    """Ensure clean state before each test by clearing all data."""
    NOTES.clear()
    USERS.clear()
    notes_index.vs = None
    yield
    NOTES.clear()
    USERS.clear()
    notes_index.vs = None


@pytest.fixture(scope="function")
def test_client():
    """Provide a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="function")
def sample_notes():
    """Provide sample notes data that can be used across tests."""
    return [
        {
            "id": "shared_note1",
            "title": "Python Programming",
            "content": "Learn Python programming language",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "programming"],
            "series": None,
            "created_at": "2025-01-01T00:00:00",
            "like_count": 10,
            "view_count": 100
        },
        {
            "id": "shared_note2",
            "title": "Machine Learning Basics",
            "content": "Introduction to machine learning concepts",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["machine-learning", "ai"],
            "series": "ML Course",
            "created_at": "2025-01-05T00:00:00",
            "like_count": 20,
            "view_count": 200
        }
    ]


@pytest.fixture(scope="function")
def sample_users():
    """Provide sample users data that can be used across tests."""
    return {
        "user1": {
            "id": "user1",
            "name": "Test User",
            "bio": "Software engineer interested in AI",
            "liked_notes": [
                {"id": "shared_note1", "tags": ["python", "programming"]}
            ],
            "recently_read_notes": [
                {"id": "shared_note1"}
            ]
        }
    }
